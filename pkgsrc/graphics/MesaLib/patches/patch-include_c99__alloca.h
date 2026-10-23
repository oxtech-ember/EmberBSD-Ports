Origin: EmberBSD; AI-assisted Mesa 26.2.4 NetBSD alloca adaptation.
Status: local; not submitted upstream.

NetBSD stdlib.h declares alloca, but strict C11/C++17 do not substitute
its compiler builtin automatically. Select caller-frame allocation in
Mesa's existing compatibility header; no libc shim or GNU-mode override.
Retain upstream VMware copyright and MIT licensing.

--- include/c99_alloca.h.orig
+++ include/c99_alloca.h
@@ -39,6 +39,13 @@
 
 #  include <alloca.h>
 
+#elif defined(__NetBSD__) && defined(__GNUC__)
+
+#  include <stdlib.h>
+
+/* Strict C/C++ modes must allocate in the caller, not call libc alloca. */
+#  define alloca(size) __builtin_alloca(size)
+
 #else /* !defined(_MSC_VER) */
 
 #  include <stdlib.h>
