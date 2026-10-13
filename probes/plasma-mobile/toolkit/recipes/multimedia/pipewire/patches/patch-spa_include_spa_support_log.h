$NetBSD$

The macOS host coefficient tools compile this header; Mach-O has no
named ELF sections, so skip the magical topic export there.

--- spa/include/spa/support/log.h.orig	2026-10-13
+++ spa/include/spa/support/log.h
@@ -337,10 +337,18 @@
  *
  * \since 1.1.0
  */
+#if defined(__APPLE__)
+/* Mach-O has no named ELF sections; the macOS host tools skip the
+ * magical topic export and register topics explicitly. */
+#define SPA_LOG_TOPIC_REGISTER(v)					      \
+	__attribute__((used))					      \
+	static struct spa_log_topic * const spa_log_topic_export_##v = &v
+#else
 #define SPA_LOG_TOPIC_REGISTER(v)		      \
 	__attribute__((used)) __attribute__((retain)) \
 	__attribute__((section("spa_log_topic"))) __attribute__((aligned(__alignof__(struct spa_log_topic *)))) \
 	static struct spa_log_topic * const spa_log_topic_export_##v = &v
+#endif
 
 /**
  * Define and magically register a \ref spa_log_topic
