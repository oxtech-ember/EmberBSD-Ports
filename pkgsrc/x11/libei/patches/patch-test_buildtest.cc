$NetBSD$

Origin: EmberBSD (AI-assisted).
The public headers declare nothing in namespace std, so with clang the
using-directive refers to an implicitly-defined namespace and -Werror
stops the build. Declare std with a standard header after the libei
headers, which keeps the check that they compile in C++.

--- test/buildtest.cc.orig
+++ test/buildtest.cc
@@ -6,6 +6,8 @@
 #include <libeis.h>
 #endif
 
+#include <cstddef>
+
 /* This is a build-test only */
 
 using namespace std;
