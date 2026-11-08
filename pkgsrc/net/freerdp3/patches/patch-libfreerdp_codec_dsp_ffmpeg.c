$NetBSD$

Use the FFmpeg 9 AAC profile name.

--- libfreerdp/codec/dsp_ffmpeg.c.orig
+++ libfreerdp/codec/dsp_ffmpeg.c
@@ -256,7 +256,11 @@
 			break;
 
 		case AV_CODEC_ID_AAC:
+#if defined(AV_PROFILE_AAC_MAIN)
+			context->context->profile = AV_PROFILE_AAC_MAIN;
+#elif defined(FF_PROFILE_AAC_MAIN)
 			context->context->profile = FF_PROFILE_AAC_MAIN;
+#endif
 			break;
 
 		default:
