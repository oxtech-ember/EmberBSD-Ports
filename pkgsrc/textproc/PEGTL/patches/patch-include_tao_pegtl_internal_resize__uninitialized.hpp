$NetBSD$

Use the public libc++ vector API; LLVM 23 removed the private __end_ member.
--- include/tao/pegtl/internal/resize_uninitialized.hpp.orig
+++ include/tao/pegtl/internal/resize_uninitialized.hpp
@@ -88,26 +88,13 @@
 
 #if defined( _LIBCPP_VECTOR )
 
-      void resize_uninitialized_proxy( std::vector< std::byte >& v, const std::size_t n ) noexcept;
-
-      template< typename T, auto M >
-      struct vector_proxy
+      // libc++ does not promise a stable private vector layout. In particular,
+      // LLVM 23 moved __end_ into a layout object. Use the public operation;
+      // resize_uninitialized() has already reserved enough capacity.
+      inline void resize_uninitialized_proxy( std::vector< std::byte >& v, const std::size_t n ) noexcept
       {
-         friend void resize_uninitialized_proxy( T& v, const std::size_t n ) noexcept
-         {
-            // v.__end_ = v.data() + n;
-            v.*M = v.data() + n;
-
-#ifndef _LIBCPP_HAS_NO_ASAN
-            __sanitizer_annotate_contiguous_container( v.data(),
-                                                       v.data() + v.capacity(),
-                                                       v.data() + v.size(),
-                                                       v.data() + n );
-#endif
-         }
-      };
-
-      template struct vector_proxy< std::vector< std::byte >, &std::vector< std::byte >::__end_ >;
+         v.resize( n );
+      }
 
 #elif defined( _MSC_VER )
 
