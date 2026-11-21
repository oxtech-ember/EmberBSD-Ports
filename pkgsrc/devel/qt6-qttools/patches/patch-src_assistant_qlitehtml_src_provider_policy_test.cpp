$NetBSD$

Exercise Qt Assistant container with a long ordinary HTML document.

--- /dev/null
+++ src/assistant/qlitehtml/src/provider_policy_test.cpp
@@ -0,0 +1,20 @@
+#include "container_qpainter.h"
+
+#include <QApplication>
+#include <QImage>
+
+int main(int argc, char **argv)
+{
+    QApplication app(argc, argv);
+    DocumentContainerContext context;
+    DocumentContainer container;
+    QImage paintDevice(640, 480, QImage::Format_ARGB32_Premultiplied);
+    container.setPaintDevice(&paintDevice);
+
+    QByteArray html("<html><body>");
+    for (int i = 0; i < 20500; ++i)
+        html += "<p>Paragraph " + QByteArray::number(i) + "</p>";
+    html += "<p id='last' name='last'>END</p></body></html>";
+    container.setDocument(html, &context);
+    return container.hasDocument() && container.anchorY(QStringLiteral("last")) >= 0 ? 0 : 1;
+}
