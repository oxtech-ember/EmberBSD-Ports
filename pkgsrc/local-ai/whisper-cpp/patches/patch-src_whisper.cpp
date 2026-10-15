$NetBSD$

Reject incomplete ASR fixed headers before consuming unwritten fields.
Return actual byte counts from the file and buffer callbacks.
Keep the C API and the existing tensor EOF behavior.
Variable-length fields, tensor payloads, and VAD parsing are outside this fix.
Origin: EmberBSD, AI-assisted; not submitted upstream.

--- src/whisper.cpp.orig
+++ src/whisper.cpp
@@ -972,9 +972,12 @@
 static whisper_global g_state;
 
 template<typename T>
-static void read_safe(whisper_model_loader * loader, T & dest) {
-    loader->read(loader->context, &dest, sizeof(T));
+static bool read_safe(whisper_model_loader * loader, T & dest) {
+    if (loader->read(loader->context, &dest, sizeof(T)) != sizeof(T)) {
+        return false;
+    }
     BYTESWAP_VALUE(dest);
+    return true;
 }
 
 static bool whisper_kv_cache_init(
@@ -1507,7 +1510,10 @@
     // verify magic
     {
         uint32_t magic;
-        read_safe(loader, magic);
+        if (!read_safe(loader, magic)) {
+            WHISPER_LOG_ERROR("%s: incomplete model header (magic)\n", __func__);
+            return false;
+        }
         if (magic != GGML_FILE_MAGIC) {
             WHISPER_LOG_ERROR("%s: invalid model data (bad magic)\n", __func__);
             return false;
@@ -1518,17 +1524,20 @@
     {
         auto & hparams = model.hparams;
 
-        read_safe(loader, hparams.n_vocab);
-        read_safe(loader, hparams.n_audio_ctx);
-        read_safe(loader, hparams.n_audio_state);
-        read_safe(loader, hparams.n_audio_head);
-        read_safe(loader, hparams.n_audio_layer);
-        read_safe(loader, hparams.n_text_ctx);
-        read_safe(loader, hparams.n_text_state);
-        read_safe(loader, hparams.n_text_head);
-        read_safe(loader, hparams.n_text_layer);
-        read_safe(loader, hparams.n_mels);
-        read_safe(loader, hparams.ftype);
+        if (!read_safe(loader, hparams.n_vocab) ||
+            !read_safe(loader, hparams.n_audio_ctx) ||
+            !read_safe(loader, hparams.n_audio_state) ||
+            !read_safe(loader, hparams.n_audio_head) ||
+            !read_safe(loader, hparams.n_audio_layer) ||
+            !read_safe(loader, hparams.n_text_ctx) ||
+            !read_safe(loader, hparams.n_text_state) ||
+            !read_safe(loader, hparams.n_text_head) ||
+            !read_safe(loader, hparams.n_text_layer) ||
+            !read_safe(loader, hparams.n_mels) ||
+            !read_safe(loader, hparams.ftype)) {
+            WHISPER_LOG_ERROR("%s: incomplete model header (hyperparameters)\n", __func__);
+            return false;
+        }
 
         assert(hparams.n_text_state == hparams.n_audio_state);
 
@@ -1589,8 +1598,11 @@
     {
         auto & filters = wctx.model.filters;
 
-        read_safe(loader, filters.n_mel);
-        read_safe(loader, filters.n_fft);
+        if (!read_safe(loader, filters.n_mel) ||
+            !read_safe(loader, filters.n_fft)) {
+            WHISPER_LOG_ERROR("%s: incomplete model header (mel filter dimensions)\n", __func__);
+            return false;
+        }
 
         filters.data.resize(filters.n_mel * filters.n_fft);
         loader->read(loader->context, filters.data.data(), filters.data.size() * sizeof(float));
@@ -3750,7 +3762,7 @@
     loader.read = [](void * ctx, void * output, size_t read_size) {
         std::ifstream * fin = (std::ifstream*)ctx;
         fin->read((char *)output, read_size);
-        return read_size;
+        return size_t(fin->gcount());
     };
 
     loader.eof = [](void * ctx) {
@@ -3790,9 +3802,13 @@
     loader.read = [](void * ctx, void * output, size_t read_size) {
         buf_context * buf = reinterpret_cast<buf_context *>(ctx);
 
-        size_t size_to_copy = buf->current_offset + read_size < buf->size ? read_size : buf->size - buf->current_offset;
+        if (buf->buffer == nullptr || buf->current_offset >= buf->size) {
+            return size_t(0);
+        }
+
+        size_t size_to_copy = std::min(read_size, buf->size - buf->current_offset);
 
-        if (size_to_copy > 0 && buf->buffer != nullptr) {
+        if (size_to_copy > 0) {
             memcpy(output, buf->buffer + buf->current_offset, size_to_copy);
         }
         buf->current_offset += size_to_copy;
