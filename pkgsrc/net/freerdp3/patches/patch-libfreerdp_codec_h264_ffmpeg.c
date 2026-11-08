$NetBSD$

FFmpeg 9 closes codecs in avcodec_free_context.

--- libfreerdp/codec/h264_ffmpeg.c.orig
+++ libfreerdp/codec/h264_ffmpeg.c
@@ -102,7 +102,9 @@
 
 	if (sys->codecEncoderContext)
 	{
+#if LIBAVCODEC_VERSION_INT < AV_VERSION_INT(61, 0, 0)
 		avcodec_close(sys->codecEncoderContext);
+#endif
 #if LIBAVCODEC_VERSION_INT >= AV_VERSION_INT(55, 69, 100)
 		avcodec_free_context(&sys->codecEncoderContext);
 #else
@@ -511,7 +513,9 @@
 
 	if (sys->codecDecoderContext)
 	{
+#if LIBAVCODEC_VERSION_INT < AV_VERSION_INT(61, 0, 0)
 		avcodec_close(sys->codecDecoderContext);
+#endif
 #if LIBAVCODEC_VERSION_INT >= AV_VERSION_INT(55, 69, 100)
 		avcodec_free_context(&sys->codecDecoderContext);
 #else
