$NetBSD$

Check allocator metadata allocations before writing through their results.
Use the existing graph allocator's unconditional fatal OOM contract.
The guards stay active in builds with NDEBUG and do not change the ABI.
Origin: EmberBSD, AI-assisted; not submitted upstream.

--- ggml/src/ggml-alloc.c.orig
+++ ggml/src/ggml-alloc.c
@@ -162,6 +162,7 @@
         return -1;
     }
     struct tallocr_chunk * chunk = calloc(1, sizeof(struct tallocr_chunk));
+    GGML_ASSERT(chunk != NULL);
     chunk->n_free_blocks = 1;
     chunk->free_blocks[0].offset = 0;
     // available space in a chunk is limited to max_chunk_size, but can be higher if:
@@ -365,6 +366,7 @@
 
 static struct ggml_dyn_tallocr * ggml_dyn_tallocr_new(size_t alignment, size_t max_buffer_size) {
     struct ggml_dyn_tallocr * alloc = (struct ggml_dyn_tallocr *)malloc(sizeof(struct ggml_dyn_tallocr));
+    GGML_ASSERT(alloc != NULL);
 
     *alloc = (struct ggml_dyn_tallocr) {
         /*.alignment      = */ alignment,
