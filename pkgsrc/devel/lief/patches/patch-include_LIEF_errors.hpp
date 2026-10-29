$NetBSD$

Allow consumers to instantiate inline templates whose shared-library definitions have hidden visibility.

--- include/LIEF/errors.hpp
+++ include/LIEF/errors.hpp
@@ -131,13 +131,5 @@
 
 }
 
-extern template class tl::expected<LIEF::ok_t, lief_errors>;
-extern template class LIEF::result<LIEF::ok_t>;
-extern template class tl::expected<uint64_t, lief_errors>;
-extern template class LIEF::result<uint64_t>;
-extern template class tl::expected<uint32_t, lief_errors>;
-extern template class LIEF::result<uint32_t>;
-extern template class tl::expected<std::string, lief_errors>;
-extern template class LIEF::result<std::string>;
 
 #endif
