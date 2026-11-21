$NetBSD$

Allow consumers to select parse limits and inspect a partial tree.

--- src/gumbo.h.orig
+++ src/gumbo.h
@@ -655,6 +655,9 @@
    * reported so we can work out something appropriate for your use-case.
    */
   GumboVector /* GumboError */ errors;
+  /** True when a resource limit stopped parsing. The partial tree is owned
+   * and released in the same way as a complete parse result. */
+  bool truncated;
 } GumboOutput;
 
 /**
@@ -673,6 +676,19 @@
 GumboOutput* gumbo_parse_with_options(
     const GumboOptions* options, const char* buffer, size_t buffer_length);
 
+/** Limits for an individual bounded parse. Open elements include implicit
+ * HTML elements. Cloned tree nodes are charged sizeof(GumboNode) plus their
+ * original tag/text length. The byte budget includes the input length. */
+typedef struct {
+  unsigned int max_open_elements;
+  size_t max_extra_clone_bytes;
+} GumboLimits;
+
+/** As gumbo_parse_with_options, but stops at a token boundary when a limit
+ * is exceeded. Pass NULL to retain the ordinary unbounded parse behavior. */
+GumboOutput* gumbo_parse_with_limits(const GumboOptions* options,
+    const char* buffer, size_t buffer_length, const GumboLimits* limits);
+
 /** Release the memory used for the parse tree & parse errors. */
 void gumbo_destroy_output(const GumboOptions* options, GumboOutput* output);
 
