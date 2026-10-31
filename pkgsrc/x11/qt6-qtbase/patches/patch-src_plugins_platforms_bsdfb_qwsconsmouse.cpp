$NetBSD$

Add absolute wscons pointer input for the framebuffer platform.

--- /dev/null
+++ src/plugins/platforms/bsdfb/qwsconsmouse.cpp
@@ -0,0 +1,168 @@
+// SPDX-License-Identifier: BSD-2-Clause
+// Origin: EmberBSD contributors (AI-assisted).
+
+#include "qwsconsmouse.h"
+#include "qbsdfbinputfailure_p.h"
+
+#include <QtCore/QFile>
+#include <QtCore/QDebug>
+#include <QtCore/QSocketNotifier>
+#include <qpa/qwindowsysteminterface.h>
+#include <QtGui/private/qguiapplication_p.h>
+#include <QtGui/private/qinputdevicemanager_p_p.h>
+#include <sys/types.h>
+#include <sys/stat.h>
+#include <sys/ioctl.h>
+#include <fcntl.h>
+#include <unistd.h>
+#include <cerrno>
+#include <utility>
+
+QT_BEGIN_NAMESPACE
+
+namespace {
+
+Qt::MouseButton qtButton(std::uint32_t bit)
+{
+    switch (bit) {
+    case 1: return Qt::LeftButton;
+    case 2: return Qt::MiddleButton;
+    case 4: return Qt::RightButton;
+    default: return Qt::NoButton;
+    }
+}
+
+} // namespace
+
+QWsconsMouse::QWsconsMouse(QString path, QBsdFb::Layout layout, QBsdFb::Rotation rotation)
+    : m_path(std::move(path)), m_layout(layout), m_rotation(rotation)
+{
+}
+
+QWsconsMouse::~QWsconsMouse()
+{
+    stop();
+}
+
+bool QWsconsMouse::start()
+{
+    if (m_fd != -1)
+        return false;
+    const auto fail = [this](const char *message) {
+        qWarning("bsdfb: %s", message);
+        stop();
+        return false;
+    };
+    const QByteArray path = QFile::encodeName(m_path);
+    m_fd = open(path.constData(), O_RDONLY | O_CLOEXEC | O_NONBLOCK | O_NOFOLLOW | O_NOCTTY);
+    if (m_fd == -1)
+        return fail("Cannot open exclusive wscons input device");
+    struct stat status{};
+    if (fstat(m_fd, &status) == -1 || !S_ISCHR(status.st_mode))
+        return fail("Input path is not a character device");
+    // Select the descriptor-local wscons_event ABI; never change the global default.
+    int version = 1;
+    if (ioctl(m_fd, WSMOUSEIO_SETVERSION, &version) == -1)
+        return fail("Cannot select wscons event version 1");
+    wsmouse_calibcoords calibration{};
+    if (ioctl(m_fd, WSMOUSEIO_GCALIBCOORDS, &calibration) == -1)
+        return fail("Cannot query absolute input calibration");
+    m_input = std::make_unique<QBsdFb::PointerInput>(m_layout, m_rotation,
+        QBsdFb::PointerInput::AxisRange{calibration.minx, calibration.maxx,
+                                       calibration.miny, calibration.maxy});
+    if (!m_input->valid())
+        return fail("Invalid absolute input calibration");
+    m_notifier = std::make_unique<QSocketNotifier>(m_fd, QSocketNotifier::Read);
+    connect(m_notifier.get(), &QSocketNotifier::activated, this,
+            [this] { readEvents(); });
+    QInputDeviceManagerPrivate::get(QGuiApplicationPrivate::inputDeviceManager())
+        ->setDeviceCount(QInputDeviceManager::DeviceTypePointer, 1);
+    m_registered = true;
+    return true;
+}
+
+void QWsconsMouse::stop()
+{
+    if (m_notifier)
+        m_notifier->setEnabled(false);
+    if (m_input)
+        m_input->disconnect([this](const auto &event) { deliver(event); });
+    if (m_registered) {
+        QInputDeviceManagerPrivate::get(QGuiApplicationPrivate::inputDeviceManager())
+            ->setDeviceCount(QInputDeviceManager::DeviceTypePointer, 0);
+        m_registered = false;
+    }
+    if (m_fd != -1) {
+        close(m_fd);
+        m_fd = -1;
+    }
+    m_records = {};
+}
+
+void QWsconsMouse::deliver(const QBsdFb::PointerInput::Output &event)
+{
+    Qt::MouseButtons buttons = Qt::NoButton;
+    for (std::uint32_t bit = 1; bit <= 4; bit <<= 1) {
+        if ((event.buttons & bit) != 0)
+            buttons |= qtButton(bit);
+    }
+    QEvent::Type type = QEvent::MouseMove;
+    if (event.kind == QBsdFb::PointerInput::Kind::Press)
+        type = QEvent::MouseButtonPress;
+    else if (event.kind == QBsdFb::PointerInput::Kind::Release)
+        type = QEvent::MouseButtonRelease;
+    const QPointF point(event.position.x, event.position.y);
+    QWindowSystemInterface::handleMouseEvent(nullptr, point, point, buttons,
+                                            qtButton(event.button), type);
+}
+
+void QWsconsMouse::readEvents()
+{
+    using Input = QBsdFb::PointerInput;
+    const auto output = [this](const Input::Output &event) { deliver(event); };
+    while (m_fd != -1) {
+        const ssize_t count = read(m_fd, m_records.writeData(), m_records.writableBytes());
+        if (count < 0) {
+            if (errno == EINTR)
+                continue;
+            if (errno == EAGAIN || errno == EWOULDBLOCK) {
+                m_input->drain(output);
+                return;
+            }
+            qWarning("bsdfb: wscons input read failed; releasing pressed buttons");
+            QBsdFb::quitAfterInputFailure([this] { stop(); });
+            return;
+        }
+        if (count == 0) {
+            qWarning("bsdfb: wscons input disconnected; releasing pressed buttons");
+            QBsdFb::quitAfterInputFailure([this] { stop(); });
+            return;
+        }
+        const bool accepted = m_records.append(static_cast<std::size_t>(count),
+            [this, &output](const wscons_event &event) {
+            switch (event.type) {
+            case WSCONS_EVENT_MOUSE_ABSOLUTE_X:
+                m_input->feed(Input::EventKind::AbsoluteX, event.value, output);
+                break;
+            case WSCONS_EVENT_MOUSE_ABSOLUTE_Y:
+                m_input->feed(Input::EventKind::AbsoluteY, event.value, output);
+                break;
+            case WSCONS_EVENT_MOUSE_DOWN:
+                m_input->feed(Input::EventKind::ButtonDown, event.value, output);
+                break;
+            case WSCONS_EVENT_MOUSE_UP:
+                m_input->feed(Input::EventKind::ButtonUp, event.value, output);
+                break;
+            default:
+                break;
+            }
+        });
+        if (!accepted) {
+            qWarning("bsdfb: Invalid wscons read length");
+            QBsdFb::quitAfterInputFailure([this] { stop(); });
+            return;
+        }
+    }
+}
+
+QT_END_NAMESPACE
