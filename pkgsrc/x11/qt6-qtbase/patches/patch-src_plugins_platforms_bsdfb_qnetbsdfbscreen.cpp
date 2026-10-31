$NetBSD$

Add checked wsdisplay framebuffer and software presentation support.

--- /dev/null
+++ src/plugins/platforms/bsdfb/qnetbsdfbscreen.cpp
@@ -0,0 +1,270 @@
+// SPDX-License-Identifier: BSD-2-Clause
+// Origin: EmberBSD contributors (AI-assisted).
+
+#include "qnetbsdfbscreen.h"
+#include "qbsdfbblit_p.h"
+#include "qwsconsmouse.h"
+
+#include <QtCore/QFile>
+#include <QtCore/QDebug>
+#include <QtGui/QWindow>
+#include <QtFbSupport/private/qfbbackingstore_p.h>
+#include <QtFbSupport/private/qfbcursor_p.h>
+#include <QtFbSupport/private/qfbwindow_p.h>
+#include <sys/types.h>
+#include <sys/stat.h>
+#include <sys/ioctl.h>
+#include <sys/mman.h>
+#include <dev/wscons/wsconsio.h>
+#include <fcntl.h>
+#include <unistd.h>
+
+QT_BEGIN_NAMESPACE
+
+namespace {
+
+class NetBsdBackingStore final : public QFbBackingStore
+{
+public:
+    NetBsdBackingStore(QWindow *window, QNetBsdFbScreen *screen)
+        : QFbBackingStore(window), m_screen(screen) {}
+
+    void resize(const QSize &size, const QRegion &contents) override
+    {
+        m_screen->backingStoreResized(window());
+        QFbBackingStore::resize(size, contents);
+    }
+
+    void flush(QWindow *window, const QRegion &region, const QPoint &offset) override
+    {
+        QFbBackingStore::flush(window, region, offset);
+        if (!mImage.isNull())
+            m_screen->backingStoreFlushed(window, mImage.size(), region);
+    }
+
+private:
+    QNetBsdFbScreen *m_screen;
+};
+
+} // namespace
+
+QNetBsdFbScreen::QNetBsdFbScreen(const QStringList &arguments)
+{
+    for (const QString &argument : arguments) {
+        if (argument.startsWith(QLatin1String("fb="))) {
+            m_fbPath = argument.mid(3);
+        } else if (argument.startsWith(QLatin1String("mouse="))) {
+            m_mousePath = argument.mid(6);
+        } else if (argument == QLatin1String("rotation=0")) {
+            m_rotation = QBsdFb::Rotation::R0;
+        } else if (argument == QLatin1String("rotation=90")) {
+            m_rotation = QBsdFb::Rotation::R90;
+        } else if (argument == QLatin1String("rotation=180")) {
+            m_rotation = QBsdFb::Rotation::R180;
+        } else if (argument == QLatin1String("rotation=270")) {
+            m_rotation = QBsdFb::Rotation::R270;
+        } else if (argument == QLatin1String("preserve=1")) {
+            m_frameGate = QBsdFb::FrameGate(true);
+        } else if (argument == QLatin1String("preserve=0")) {
+            m_frameGate = QBsdFb::FrameGate(false);
+        } else {
+            m_argumentsValid = false;
+        }
+    }
+    m_argumentsValid = m_argumentsValid && m_fbPath.startsWith(QLatin1Char('/'))
+        && m_mousePath.startsWith(QLatin1Char('/'));
+}
+
+QNetBsdFbScreen::~QNetBsdFbScreen()
+{
+    // The notifier must stop before the screen or its mapping goes away.
+    m_mouse.reset();
+    closeFramebuffer();
+}
+
+void QNetBsdFbScreen::closeFramebuffer()
+{
+    // Destroy all Qt views of the device before unmapping it.
+    m_onscreenImage = QImage();
+    if (m_hasMapping) {
+        if (munmap(m_mapping, m_layout.mapLength) == -1)
+            qWarning("bsdfb: Failed to unmap framebuffer");
+        m_mapping = nullptr;
+        m_hasMapping = false;
+    }
+    if (m_fd != -1) {
+        if (m_modeChanged && ioctl(m_fd, WSDISPLAYIO_SMODE, &m_savedMode) == -1)
+            qWarning("bsdfb: Failed to restore display mode");
+        close(m_fd);
+        m_fd = -1;
+    }
+    m_modeChanged = false;
+}
+
+bool QNetBsdFbScreen::initialize()
+{
+    if (!m_argumentsValid || m_fd != -1) {
+        qWarning("bsdfb: Invalid arguments or repeated initialization");
+        return false;
+    }
+    const auto fail = [this](const char *message) {
+        qWarning("bsdfb: %s", message);
+        closeFramebuffer();
+        return false;
+    };
+
+    const QByteArray path = QFile::encodeName(m_fbPath);
+    m_fd = open(path.constData(), O_RDWR | O_CLOEXEC | O_NOFOLLOW | O_NOCTTY | O_NONBLOCK);
+    if (m_fd == -1)
+        return fail("Cannot open display device");
+    struct stat status{};
+    if (fstat(m_fd, &status) == -1 || !S_ISCHR(status.st_mode))
+        return fail("Display path is not a character device");
+    if (ioctl(m_fd, WSDISPLAYIO_GMODE, &m_savedMode) == -1)
+        return fail("Cannot read display mode");
+    wsdisplayio_fbinfo fb{};
+    if (ioctl(m_fd, WSDISPLAYIO_GET_FBINFO, &fb) == -1)
+        return fail("Cannot query framebuffer layout");
+    const auto &rgb = fb.fbi_subtype.fbi_rgbmasks;
+    QBsdFb::FrameInfo info;
+    info.fbsize = fb.fbi_fbsize;
+    info.offset = fb.fbi_fboffset;
+    info.width = fb.fbi_width;
+    info.height = fb.fbi_height;
+    info.stride = fb.fbi_stride;
+    info.bpp = fb.fbi_bitsperpixel;
+    info.pixelType = fb.fbi_pixeltype;
+    info.flags = fb.fbi_flags;
+    info.redOffset = rgb.red_offset;
+    info.redSize = rgb.red_size;
+    info.greenOffset = rgb.green_offset;
+    info.greenSize = rgb.green_size;
+    info.blueOffset = rgb.blue_offset;
+    info.blueSize = rgb.blue_size;
+    info.alphaOffset = rgb.alpha_offset;
+    info.alphaSize = rgb.alpha_size;
+    if (!QBsdFb::makeLayout(info, m_layout))
+        return fail("Unsupported or invalid linear RGB32 framebuffer layout");
+
+    QImage::Format nativeFormat = QImage::Format_RGB32;
+    if (m_layout.format == QBsdFb::PixelFormat::Xbgr8888) {
+#if Q_BYTE_ORDER == Q_LITTLE_ENDIAN
+        nativeFormat = QImage::Format_RGBX8888;
+#else
+        return fail("Unsupported red-low RGB32 framebuffer on big-endian target");
+#endif
+    }
+    // Reject unsupported buffers without changing the current display mode.
+    if (m_savedMode != WSDISPLAYIO_MODE_DUMBFB) {
+        int mode = WSDISPLAYIO_MODE_DUMBFB;
+        m_modeChanged = true; // Also attempt restoration after a failed transition.
+        if (ioctl(m_fd, WSDISPLAYIO_SMODE, &mode) == -1)
+            return fail("Cannot select dumb framebuffer mode");
+    }
+    void *mapping = mmap(nullptr, m_layout.mapLength, PROT_READ | PROT_WRITE,
+                         MAP_SHARED, m_fd, 0);
+    if (mapping == MAP_FAILED)
+        return fail("Cannot map framebuffer");
+    m_mapping = mapping;
+    m_hasMapping = true;
+    if (mapping == nullptr)
+        return fail("Cannot use a null-address mapping as a Qt image");
+    m_onscreenImage = QImage(static_cast<uchar *>(mapping) + m_layout.dataOffset,
+                            m_layout.nativeWidth, m_layout.nativeHeight,
+                            m_layout.stride, nativeFormat);
+    if (m_onscreenImage.isNull())
+        return fail("Cannot create framebuffer image view");
+
+    const auto size = QBsdFb::logicalSize(m_layout, m_rotation);
+    mGeometry = QRect(0, 0, size.width, size.height);
+    mPhysicalSize = QSizeF(size.width * 25.4 / 100, size.height * 25.4 / 100);
+    mDepth = 32;
+    mFormat = QImage::Format_RGB32;
+    initializeCompositor();
+    if (mScreenImage.isNull())
+        return fail("Cannot allocate compositor image");
+    mCursor = new QFbCursor(this);
+    mCursor->setParent(this);
+    return true;
+}
+
+bool QNetBsdFbScreen::initializeInput()
+{
+    if (qEnvironmentVariableIntValue("QT_QPA_FB_DISABLE_INPUT"))
+        return true;
+    m_mouse = std::make_unique<QWsconsMouse>(m_mousePath, m_layout, m_rotation);
+    if (!m_mouse->start()) {
+        m_mouse.reset();
+        return false;
+    }
+    return true;
+}
+
+QPlatformBackingStore *QNetBsdFbScreen::createBackingStore(QWindow *window)
+{
+    return new NetBsdBackingStore(window, this);
+}
+
+void QNetBsdFbScreen::backingStoreResized(QWindow *window)
+{
+    if (!m_frameGate.hasPresentedFrame() && m_frameWindow == window)
+        m_frameGate.resetForWindow(reinterpret_cast<quintptr>(window), window->size());
+}
+
+void QNetBsdFbScreen::backingStoreFlushed(QWindow *window, const QSize &imageSize,
+                                        const QRegion &region)
+{
+    if (m_frameGate.hasPresentedFrame() || !window || !window->isVisible()
+        || topWindow() != window || imageSize.width() < window->width()
+        || imageSize.height() < window->height())
+        return;
+    const quintptr id = reinterpret_cast<quintptr>(window);
+    if (m_frameWindow != window) {
+        m_frameWindow = window;
+        m_frameGate.resetForWindow(id, window->size());
+    }
+    if (m_frameGate.addFlush(id, window->size(), region)) {
+        m_readyFrameSize = window->size();
+        setDirty(mGeometry);
+    }
+}
+
+QRegion QNetBsdFbScreen::doRedraw()
+{
+    if (!m_frameGate.hasPresentedFrame() && m_frameGate.allowsRedraw()
+        && (!m_frameWindow || !m_frameWindow->isVisible()
+            || topWindow() != m_frameWindow || m_frameWindow->size() != m_readyFrameSize)) {
+        // A flush is only a candidate until its window is composited and copied out.
+        m_frameGate.resetForWindow(0, QSize());
+        m_frameWindow.clear();
+    }
+    const QRegion touched = QFbScreen::doRedraw();
+    if (!m_frameGate.allowsRedraw() || m_onscreenImage.isNull() || touched.isEmpty())
+        return {};
+
+    if (!QBsdFb::blit(m_onscreenImage, mScreenImage, m_layout, m_rotation, touched)) {
+        qWarning("bsdfb: Cannot paint framebuffer image");
+        return {};
+    }
+    m_frameGate.framePresented();
+    return touched;
+}
+
+QPixmap QNetBsdFbScreen::grabWindow(WId id, int x, int y, int width, int height) const
+{
+    QRect bounds = mGeometry;
+    if (id) {
+        const QFbWindow *window = windowForId(id);
+        if (!window)
+            return {};
+        bounds = window->geometry();
+    }
+    if (width < 0)
+        width = bounds.width() - x;
+    if (height < 0)
+        height = bounds.height() - y;
+    const QRect selection(bounds.x() + x, bounds.y() + y, width, height);
+    return QPixmap::fromImage(mScreenImage.copy(selection.intersected(mGeometry)));
+}
+
+QT_END_NAMESPACE
