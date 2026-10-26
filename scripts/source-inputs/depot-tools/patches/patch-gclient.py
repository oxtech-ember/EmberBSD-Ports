$NetBSD$

Keep complete CIPD version tags containing @ in revinfo JSON. For example,
version:3@4.60.4 must not silently become version:3 in deferred input inventory.
Origin: EmberBSD (AI-assisted), not submitted upstream.

--- gclient.py.orig
+++ gclient.py
@@ -3016,8 +3016,8 @@
             if self._options.output_json:
                 json_output = {
                     name: {
-                        "url": rev.split("@")[0] if rev else None,
-                        "rev": rev.split("@")[1]
+                        "url": rev.split("@", 1)[0] if rev else None,
+                        "rev": rev.split("@", 1)[1]
                         if rev and "@" in rev
                         else None,
                     }
