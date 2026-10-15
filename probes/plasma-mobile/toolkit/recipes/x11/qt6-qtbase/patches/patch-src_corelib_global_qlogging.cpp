$NetBSD$

Origin: AI-assisted EmberBSD adaptation for Qt 6.12.0, not submitted upstream.

Decode a copied frame pointer instead of requiring mutable backtrace storage.
Handle allocation failure before reading backtrace_symbols results.
Use NetBSD's formatting API to supply the existing parser's symbol syntax.
Other platforms retain their backtrace_symbols implementation.

--- src/corelib/global/qlogging.cpp.orig
+++ src/corelib/global/qlogging.cpp
@@ -1564,10 +1564,17 @@
     // This code is protected by QMessagePattern::mutex so it is thread safe on all compilers
     static const QRegularExpression rx(QStringLiteral("^(?:[^(]*/)?([^(/]+)\\(([^+]*)(?:[\\+[a-f0-9x]*)?\\) \\[[a-f0-9x]*\\]$"));
 
-    auto decodeFrame = [&](void *&addr) -> DecodedFrame {
+    auto decodeFrame = [&](void *addr) -> DecodedFrame {
         auto cleanup = [](auto *p) { free(p); };
+#    if defined(Q_OS_NETBSD)
+        auto strings = std::unique_ptr<char *, decltype(cleanup)>(
+                backtrace_symbols_fmt(&addr, 1, "%f(%n%D) [%a]"), cleanup);
+#    else
         auto strings =
             std::unique_ptr<char *, decltype(cleanup)>(backtrace_symbols(&addr, 1), cleanup);
+#    endif
+        if (!strings)
+            return {};
         QString trace = QString::fromUtf8(strings.get()[0]);
         QRegularExpressionMatch m = rx.match(trace);
         if (!m.hasMatch())
