$NetBSD$

Preserve the upstream cross-compilation locale guess; native tests are unchanged.
Origin: EmberBSD (AI-assisted).

--- m4/strcasecmp.m4.orig
+++ m4/strcasecmp.m4
@@ -57,7 +57,7 @@
           gl_cv_func_strcasecmp_works=no
         fi
        ],
-       [])
+       [:])
     ])
 ])
 
