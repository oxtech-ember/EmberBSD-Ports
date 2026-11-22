$NetBSD$

Handle SimpleCpp stringify warnings with the other portability notices.
Origin: EmberBSD contributors (AI-assisted), not submitted upstream.

--- lib/preprocessor.cpp.orig
+++ lib/preprocessor.cpp
@@ -947,6 +947,7 @@
         case simplecpp::Output::PORTABILITY_BACKSLASH:
         case simplecpp::Output::PORTABILITY_LINE_DIRECTIVE:
         case simplecpp::Output::PORTABILITY_NO_EOF_NEWLINE:
+        case simplecpp::Output::PORTABILITY_STRINGIFY:
             break;
         case simplecpp::Output::MISSING_HEADER: {
             // not considered an "error"
@@ -1001,6 +1002,7 @@
     case simplecpp::Output::PORTABILITY_BACKSLASH:
     case simplecpp::Output::PORTABILITY_LINE_DIRECTIVE:
     case simplecpp::Output::PORTABILITY_NO_EOF_NEWLINE:
+    case simplecpp::Output::PORTABILITY_STRINGIFY:
         throw std::runtime_error("unexpected simplecpp::Output type " + std::to_string(type));
     }
 
