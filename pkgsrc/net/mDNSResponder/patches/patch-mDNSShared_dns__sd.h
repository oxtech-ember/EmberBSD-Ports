# Lint uses Clang preprocessing but does not parse fixed enums or nullability.
# Select the existing portable branches for lint only.
--- mDNSShared/dns_sd.h.orig
+++ mDNSShared/dns_sd.h
@@ -165,7 +165,7 @@
     #define __has_feature(X)                0
 #endif
 
-#if __has_feature(objc_fixed_enum) || __has_extension(cxx_fixed_enum) || __has_extension(cxx_strong_enums)
+#if !defined(__lint__) && (__has_feature(objc_fixed_enum) || __has_extension(cxx_fixed_enum) || __has_extension(cxx_strong_enums))
     #define DNS_SERVICE_FLAGS_ENUM          enum : uint32_t
 #else
     #define DNS_SERVICE_FLAGS_ENUM          enum
@@ -176,7 +176,7 @@
 #endif
 
 #ifndef DNS_SD_NULLABLE
-    #if __has_feature(nullability)
+    #if !defined(__lint__) && __has_feature(nullability)
         #define DNS_SD_NULLABLE             _Nullable
         #define DNS_SD_NONNULL              _Nonnull
     #else
