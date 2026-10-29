$NetBSD$

Include the declaration of std::terminate directly.
Origin: EmberBSD contributors (AI-assisted).

--- include/tcb/span.hpp.orig
+++ include/tcb/span.hpp
@@ -14,6 +14,7 @@
 #include <array>
 #include <cstddef>
 #include <cstdint>
+#include <exception>
 #include <type_traits>
 
 #ifndef TCB_SPAN_NO_EXCEPTIONS
