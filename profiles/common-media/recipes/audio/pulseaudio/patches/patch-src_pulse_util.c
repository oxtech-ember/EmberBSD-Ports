$NetBSD$

Origin: EmberBSD (AI-assisted). Not submitted upstream.
The dladdr fallback must fill and return the caller's bounded buffer,
matching every other pa_get_binary_name branch. Release the temporary path.

--- src/pulse/util.c.orig
+++ src/pulse/util.c
@@ -261,8 +261,11 @@
             int err = dladdr(&_main, &info);
             if (err != 0) {
                 char *p = pa_realpath(info.dli_fname);
-                if (p)
-                    return p;
+                if (p) {
+                    pa_strlcpy(s, pa_path_get_filename(p), l);
+                    pa_xfree(p);
+                    return s;
+                }
             }
         }
     }
