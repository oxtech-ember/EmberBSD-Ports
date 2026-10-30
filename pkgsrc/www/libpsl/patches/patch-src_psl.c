$NetBSD$

Expose exact PSL rule lookup for DAFSA and parsed contexts.

--- src/psl.c.orig
+++ src/psl.c
@@ -66,6 +66,7 @@
 #include <time.h>
 #include <errno.h>
 #include <limits.h> /* for UINT_MAX */
+#include <stdint.h> /* for PTRDIFF_MAX */
 
 #ifdef HAVE_NL_LANGINFO
 # include <langinfo.h>
@@ -843,6 +844,41 @@
 int LookupStringInFixedSet(const unsigned char* graph, size_t length, const char* key, size_t key_length);
 int GetUtfMode(const unsigned char *graph, size_t length);
 
+int
+psl_lookup_rule(const psl_ctx_t *psl, const char *domain, size_t length)
+{
+    psl_entry_t key = {0};
+    psl_entry_t *rule;
+    size_t i;
+    int flags;
+
+    if (!psl || !domain || !length || length > PTRDIFF_MAX || memchr(domain, 0, length))
+        return -1;
+    if (psl == &builtin_psl || psl->dafsa) {
+        const unsigned char *data = psl == &builtin_psl ? kDafsa : psl->dafsa;
+        size_t size = psl == &builtin_psl ? sizeof(kDafsa) : psl->dafsa_size;
+        flags = LookupStringInFixedSet(data, size, domain, length);
+    } else {
+        /* suffix_init stores fewer than sizeof(label_buf) - 1 bytes. */
+        if (length >= sizeof(key.label_buf) - 1)
+            return -1;
+        key.label = domain;
+        key.length = length;
+        key.nlabels = 1;
+        for (i = 0; i < length; ++i) {
+            if (domain[i] == '.') {
+                if (key.nlabels == 255)
+                    return -1;
+                ++key.nlabels;
+            }
+        }
+        rule = vector_get(psl->suffixes, vector_find(psl->suffixes, &key));
+        flags = rule ? rule->flags : -1;
+    }
+    return flags < 0 ? -1 : flags & (PSL_RULE_EXCEPTION | PSL_RULE_WILDCARD |
+        PSL_RULE_ICANN | PSL_RULE_PRIVATE);
+}
+
 static int is_public_suffix(const psl_ctx_t *psl, const char *domain, int type)
 {
 	psl_entry_t suffix;
