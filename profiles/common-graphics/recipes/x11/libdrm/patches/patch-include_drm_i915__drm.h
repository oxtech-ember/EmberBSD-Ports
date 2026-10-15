Origin: EmberBSD; AI-assisted GCC16 diagnostics for unchanged imported ABI records.

Keep each packed attribute and report unnecessary-packing diagnostics as warnings.

--- include/drm/i915_drm.h.orig
+++ include/drm/i915_drm.h
@@ -2220,6 +2220,11 @@
  * the backing engines (bypassing the load balancing proxy), the context must
  * be defined to use a single timeline for all engines.
  */
+/* Preserve this imported uAPI layout; keep the GCC diagnostic visible. */
+#if defined(__GNUC__) && !defined(__clang__) && __GNUC__ >= 16
+#pragma GCC diagnostic push
+#pragma GCC diagnostic warning "-Wpacked"
+#endif
 struct i915_context_engines_load_balance {
 	struct i915_user_extension base;
 
@@ -2231,6 +2236,9 @@
 
 	struct i915_engine_class_instance engines[];
 } __attribute__((packed));
+#if defined(__GNUC__) && !defined(__clang__) && __GNUC__ >= 16
+#pragma GCC diagnostic pop
+#endif
 
 #define I915_DEFINE_CONTEXT_ENGINES_LOAD_BALANCE(name__, N__) struct { \
 	struct i915_user_extension base; \
@@ -2256,6 +2264,11 @@
  * To execute a request in parallel on the master engine and a sibling requires
  * coordination with a I915_EXEC_FENCE_SUBMIT.
  */
+/* Preserve this imported uAPI layout; keep the GCC diagnostic visible. */
+#if defined(__GNUC__) && !defined(__clang__) && __GNUC__ >= 16
+#pragma GCC diagnostic push
+#pragma GCC diagnostic warning "-Wpacked"
+#endif
 struct i915_context_engines_bond {
 	struct i915_user_extension base;
 
@@ -2269,6 +2282,9 @@
 
 	struct i915_engine_class_instance engines[];
 } __attribute__((packed));
+#if defined(__GNUC__) && !defined(__clang__) && __GNUC__ >= 16
+#pragma GCC diagnostic pop
+#endif
 
 #define I915_DEFINE_CONTEXT_ENGINES_BOND(name__, N__) struct { \
 	struct i915_user_extension base; \
@@ -2350,6 +2366,11 @@
  *	CS[0], CS[1]
  *	CS[1], CS[3] - Not logically contiguous, return -EINVAL
  */
+/* Preserve this imported uAPI layout; keep the GCC diagnostic visible. */
+#if defined(__GNUC__) && !defined(__clang__) && __GNUC__ >= 16
+#pragma GCC diagnostic push
+#pragma GCC diagnostic warning "-Wpacked"
+#endif
 struct i915_context_engines_parallel_submit {
 	/**
 	 * @base: base user extension.
@@ -2397,6 +2418,9 @@
 	struct i915_engine_class_instance engines[];
 
 } __attribute__((packed));
+#if defined(__GNUC__) && !defined(__clang__) && __GNUC__ >= 16
+#pragma GCC diagnostic pop
+#endif
 
 #define I915_DEFINE_CONTEXT_ENGINES_PARALLEL_SUBMIT(name__, N__) struct { \
 	struct i915_user_extension base; \
@@ -2464,6 +2488,11 @@
  * 	gem_execbuf(drm_fd, &execbuf);
  */
 
+/* Preserve this imported uAPI layout; keep the GCC diagnostic visible. */
+#if defined(__GNUC__) && !defined(__clang__) && __GNUC__ >= 16
+#pragma GCC diagnostic push
+#pragma GCC diagnostic warning "-Wpacked"
+#endif
 struct i915_context_param_engines {
 	__u64 extensions; /* linked chain of extension blocks, 0 terminates */
 #define I915_CONTEXT_ENGINES_EXT_LOAD_BALANCE 0 /* see i915_context_engines_load_balance */
@@ -2471,6 +2500,9 @@
 #define I915_CONTEXT_ENGINES_EXT_PARALLEL_SUBMIT 2 /* see i915_context_engines_parallel_submit */
 	struct i915_engine_class_instance engines[0];
 } __attribute__((packed));
+#if defined(__GNUC__) && !defined(__clang__) && __GNUC__ >= 16
+#pragma GCC diagnostic pop
+#endif
 
 #define I915_DEFINE_CONTEXT_PARAM_ENGINES(name__, N__) struct { \
 	__u64 extensions; \
