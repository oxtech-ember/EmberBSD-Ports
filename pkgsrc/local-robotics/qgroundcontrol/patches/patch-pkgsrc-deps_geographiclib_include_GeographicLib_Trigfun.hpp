$NetBSD$

Origin: EmberBSD (AI-assisted), local, not submitted upstream.
Include <vector>: the header uses std::vector, and libc++ does not
provide it through <functional>.

--- pkgsrc-deps/geographiclib/include/GeographicLib/Trigfun.hpp.orig
+++ pkgsrc-deps/geographiclib/include/GeographicLib/Trigfun.hpp
@@ -14,6 +14,7 @@
 
 #include <functional>
 #include <utility>
+#include <vector>
 
 #if defined(_MSC_VER)
 // Squelch warnings about dll vs vector
