$NetBSD$

Origin: EmberBSD, OpenAI Codex (GPT-6), AI-assisted; not submitted upstream.
Enumerate NetBSD serial identities through read-only drvctl properties.
Keep dial-out aliases and symlinks without probing serial devices.

--- /dev/null
+++ src/serialport/qserialportinfo_netbsd.cpp
@@ -0,0 +1,160 @@
+// EmberBSD, AI-assisted with OpenAI Codex (GPT-6).
+// SPDX-License-Identifier: LicenseRef-Qt-Commercial OR LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only
+
+#include "qserialportinfo.h"
+#include "qserialportinfo_p.h"
+#include "qserialportinfo_netbsd_p.h"
+
+#include <QtCore/qdir.h>
+#include <QtCore/qfile.h>
+#include <QtCore/qhash.h>
+#include <QtCore/qregularexpression.h>
+#include <private/qcore_unix_p.h>
+
+#include <sys/drvctlio.h>
+#include <sys/stat.h>
+#include <prop/proplib.h>
+#include <utility>
+
+QT_BEGIN_NAMESPACE
+
+namespace {
+
+class Properties
+{
+public:
+    prop_dictionary_t value = nullptr;
+    explicit Properties(prop_dictionary_t dictionary = nullptr) : value(dictionary) {}
+    ~Properties() { if (value) prop_object_release(value); }
+    Properties(const Properties &) = delete;
+    Properties &operator=(const Properties &) = delete;
+    Properties(Properties &&other) noexcept : value(std::exchange(other.value, nullptr)) {}
+};
+
+Properties deviceProperties(int fd, const QByteArray &name)
+{
+    Properties command(prop_dictionary_create());
+    Properties arguments(prop_dictionary_create());
+    Properties reply;
+    if (!command.value || !arguments.value
+            || !prop_dictionary_set_string(command.value, "drvctl-command", "get-properties")
+            || !prop_dictionary_set_string(arguments.value, "device-name", name.constData())
+            || !prop_dictionary_set(command.value, "drvctl-arguments", arguments.value)
+            || prop_dictionary_sendrecv_ioctl(command.value, fd, DRVCTLCOMMAND, &reply.value))
+        return Properties();
+
+    int error = 0;
+    if (!reply.value || !prop_dictionary_get_int(reply.value, "drvctl-error", &error) || error)
+        return Properties();
+    prop_object_t data = prop_dictionary_get(reply.value, "drvctl-result-data");
+    if (!data || prop_object_type(data) != PROP_TYPE_DICTIONARY)
+        return Properties();
+    prop_object_retain(data);
+    return Properties(static_cast<prop_dictionary_t>(data));
+}
+
+QString stringProperty(prop_dictionary_t dictionary, const char *key)
+{
+    const char *text = nullptr;
+    if (!dictionary || !prop_dictionary_get_string(dictionary, key, &text))
+        return QString();
+    return QString::fromUtf8(text);
+}
+
+void usbProperties(int fd, const Properties &serial, QSerialPortInfoPrivate &port)
+{
+    QByteArray parent = stringProperty(serial.value, "device-parent").toLocal8Bit();
+    // USB serial interfaces can have an intermediate interface or bridge node.
+    // Bound the walk even if a damaged property graph contains a cycle.
+    for (int depth = 0; depth < 8 && !parent.isEmpty(); ++depth) {
+        const auto properties = deviceProperties(fd, parent);
+        if (!properties.value)
+            return;
+        uint16_t vendor = 0;
+        uint16_t product = 0;
+        const bool hasVendor = prop_dictionary_get_uint16(properties.value, "vendor-id", &vendor);
+        const bool hasProduct = prop_dictionary_get_uint16(properties.value, "product-id", &product);
+        if (hasVendor || hasProduct) {
+            port.vendorIdentifier = vendor;
+            port.productIdentifier = product;
+            port.hasVendorIdentifier = hasVendor;
+            port.hasProductIdentifier = hasProduct;
+            port.description = stringProperty(properties.value, "product-string");
+            port.manufacturer = stringProperty(properties.value, "vendor-string");
+            port.serialNumber = stringProperty(properties.value, "serialnumber");
+            return;
+        }
+        parent = stringProperty(properties.value, "device-parent").toLocal8Bit();
+    }
+}
+
+} // namespace
+
+QList<QSerialPortInfo> QSerialPortInfo::availablePorts()
+{
+    QList<QSerialPortInfo> result;
+    QHash<quint64, QSerialPortInfoPrivate> devices;
+    const QDir directory(QStringLiteral("/dev"));
+    const auto entries = directory.entryInfoList(QDir::Files | QDir::System | QDir::NoDotAndDotDot);
+    const QRegularExpression usbName(QStringLiteral("^dtyU([0-9]+)$"));
+    const int fd = qt_safe_open(DRVCTLDEV, O_RDONLY);
+
+    // Seed the identity map from dial-out nodes. Never open a serial port:
+    // opening can wait for DCD, assert DTR, or interfere with its current owner.
+    for (const auto &entry : entries) {
+        const QString name = entry.fileName();
+        if (!QSerialPortInfoNetBSDPrivate::isDialoutDeviceName(name))
+            continue;
+        struct stat info;
+        const auto path = QFile::encodeName(entry.absoluteFilePath());
+        if (::stat(path.constData(), &info) != 0 || !S_ISCHR(info.st_mode))
+            continue;
+        QSerialPortInfoPrivate port;
+        const auto match = usbName.match(name);
+        if (match.hasMatch() && fd >= 0) {
+            const auto serial = deviceProperties(fd, "ucom" + match.captured(1).toLatin1());
+            if (!serial.value)
+                continue; // A static /dev node does not mean hardware is attached.
+            usbProperties(fd, serial, port);
+        }
+        if (!devices.contains(quint64(info.st_rdev))
+                || port.hasVendorIdentifier || port.hasProductIdentifier)
+            devices.insert(quint64(info.st_rdev), port);
+    }
+    if (fd >= 0)
+        qt_safe_close(fd);
+
+    // Include character aliases and symbolic links only when their device
+    // identity matches a serial node. This also keeps configured stable names.
+    for (const auto &entry : entries) {
+        struct stat info;
+        const auto path = QFile::encodeName(entry.absoluteFilePath());
+        if (::stat(path.constData(), &info) != 0 || !S_ISCHR(info.st_mode))
+            continue;
+        const auto found = devices.constFind(quint64(info.st_rdev));
+        if (found == devices.cend())
+            continue;
+        QSerialPortInfoPrivate port = found.value();
+        port.device = entry.absoluteFilePath();
+        port.portName = entry.fileName();
+        // The dial-in and control nodes use different minor numbers. Include
+        // only the dial-out identity and its aliases, without duplicates.
+        result.append(port);
+    }
+    return result;
+}
+
+QString QSerialPortInfoPrivate::portNameToSystemLocation(const QString &source)
+{
+    return (source.startsWith(QLatin1Char('/'))
+            || source.startsWith(QLatin1String("./"))
+            || source.startsWith(QLatin1String("../")))
+            ? source : (QLatin1String("/dev/") + source);
+}
+
+QString QSerialPortInfoPrivate::portNameFromSystemLocation(const QString &source)
+{
+    return source.startsWith(QLatin1String("/dev/")) ? source.mid(5) : source;
+}
+
+QT_END_NAMESPACE
