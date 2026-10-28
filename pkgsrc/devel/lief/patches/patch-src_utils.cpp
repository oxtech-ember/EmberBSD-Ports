$NetBSD$

Adapt to the selected current shared dependency API.

--- src/utils.cpp.orig
+++ src/utils.cpp
@@ -38,7 +38,7 @@
   using namespace utf8;
   using namespace utf8::internal;
   utfchar32_t cp = 0;
-  internal::utf_error err_code = validate_next(it, end, cp);
+  internal::utf_error err_code = decode_next(it, end, cp);
   switch (err_code) {
     case UTF8_OK: break;
     case NOT_ENOUGH_ROOM: return make_error_code(lief_errors::data_too_large);
