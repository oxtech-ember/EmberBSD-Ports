$NetBSD: patch-src_multimedia_audio_qaudiosystem__p.h,v 1.1 2026/04/30 06:38:39 adam Exp $

Origin: pkgsrc; AI-assisted EmberBSD refresh for Qt 6.12.0, not submitted upstream.

Preserve the NetBSD alloca branch with the upstream nonblocking annotation.

--- src/multimedia/audio/qaudiosystem_p.h.orig
+++ src/multimedia/audio/qaudiosystem_p.h
@@ -229,7 +229,7 @@
 inline auto withTemporaryBuffer(size_t bufferSize, Functor &&f) noexcept Q_DECL_NONBLOCKING_FUNCTION
 {
     if (bufferSize <= limit) Q_LIKELY_BRANCH {
-#ifdef alloca
+#if defined(alloca) || defined(__NetBSD__)
         std::byte *stackBuffer = reinterpret_cast<std::byte *>(alloca(bufferSize));
         auto stackBufferSpan = QSpan<std::byte>{
             stackBuffer,
