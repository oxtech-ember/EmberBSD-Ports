$NetBSD$

NetBSD has no ECHRNG errno; use ERANGE for the same overflow report.

--- spa/include/spa/param/audio/layout-types.h.orig	2026-10-13
+++ spa/include/spa/param/audio/layout-types.h
@@ -78,6 +78,11 @@
 	{ NULL, { 0, { SPA_AUDIO_CHANNEL_UNKNOWN } } },
 };
 
+/* NetBSD has no ECHRNG errno; use ERANGE for the same overflow report. */
+#if defined(__NetBSD__)
+#define ECHRNG ERANGE
+#endif
+
 SPA_API_AUDIO_LAYOUT_TYPES int
 spa_audio_layout_info_parse_name(struct spa_audio_layout_info *layout, size_t size,
 		const char *name)
