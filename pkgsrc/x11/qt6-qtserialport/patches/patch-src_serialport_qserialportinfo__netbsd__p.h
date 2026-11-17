$NetBSD$

Origin: EmberBSD, OpenAI Codex (GPT-6), AI-assisted; not submitted upstream.
Enumerate NetBSD serial identities through read-only drvctl properties.
Keep dial-out aliases and symlinks without probing serial devices.

--- /dev/null
+++ src/serialport/qserialportinfo_netbsd_p.h
@@ -0,0 +1,35 @@
+// EmberBSD, AI-assisted with OpenAI Codex (GPT-6).
+// SPDX-License-Identifier: LicenseRef-Qt-Commercial OR LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only
+
+#ifndef QSERIALPORTINFO_NETBSD_P_H
+#define QSERIALPORTINFO_NETBSD_P_H
+
+//
+//  W A R N I N G
+//  -------------
+//
+// This file is not part of the Qt API. It exists purely as an
+// implementation detail and may change or be removed without notice.
+//
+// We mean it.
+//
+
+#include <QtCore/qregularexpression.h>
+
+QT_BEGIN_NAMESPACE
+
+namespace QSerialPortInfoNetBSDPrivate {
+
+inline bool isDialoutDeviceName(const QString &name)
+{
+    // Device families and decimal unit spellings from NetBSD MAKEDEV.
+    static const QRegularExpression serialName(QStringLiteral(
+            R"(\Adty(?:[0-9]{2}|[ACSUYZh][0-9]+|CY[0-9]{3}|CZ[0-9]{4}|TX0[0-9]+|HS[0-9]+\.[0-9]+)\z)"));
+    return serialName.match(name).hasMatch();
+}
+
+} // namespace QSerialPortInfoNetBSDPrivate
+
+QT_END_NAMESPACE
+
+#endif
