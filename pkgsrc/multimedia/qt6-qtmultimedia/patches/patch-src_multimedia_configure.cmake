$NetBSD$

Origin: AI-assisted EmberBSD adaptation for Qt 6.12.0, not submitted upstream.

Allow FFmpeg video on NetBSD without a low-level audio backend.
QPlatformAudioDevices already provides the upstream no-device implementation.
Keep audio unavailable there; FFmpeg discovery and thread support are required.

--- src/multimedia/configure.cmake.orig
+++ src/multimedia/configure.cmake
@@ -290,7 +290,7 @@
     ENABLE INPUT_ffmpeg STREQUAL 'yes'
     DISABLE INPUT_ffmpeg STREQUAL 'no'
     CONDITION FFmpeg_FOUND
-              AND (APPLE OR WIN32 OR ANDROID OR QNX OR QT_FEATURE_pulseaudio OR QT_FEATURE_pipewire)
+              AND (APPLE OR WIN32 OR ANDROID OR QNX OR NETBSD OR QT_FEATURE_pulseaudio OR QT_FEATURE_pipewire)
               AND QT_FEATURE_thread
 )
 
