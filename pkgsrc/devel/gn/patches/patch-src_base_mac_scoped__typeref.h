$NetBSD$

Keep Objective-C ownership annotations in Objective-C translation units.
C++ CoreFoundation references keep the same explicit Traits retain/release.
Preserve the upstream Chromium copyright and BSD-style license.
Origin: EmberBSD (AI-assisted), not submitted upstream.

--- src/base/mac/scoped_typeref.h.orig
+++ src/base/mac/scoped_typeref.h
@@ -8,6 +8,16 @@
 #include "base/compiler_specific.h"
 #include "base/logging.h"
 #include "base/memory/scoped_policy.h"
+
+// Objective-C ownership annotations do not apply to C++ CF references.
+// Traits still perform the actual Retain and Release operations in both modes.
+#if defined(__OBJC__)
+#define GN_SCOPED_UNRETAINED __unsafe_unretained
+#define GN_SCOPED_NOT_RETAINED __attribute((ns_returns_not_retained))
+#else
+#define GN_SCOPED_UNRETAINED
+#define GN_SCOPED_NOT_RETAINED
+#endif
 
 namespace base {
 
@@ -54,7 +64,7 @@
   typedef T element_type;
 
   explicit constexpr ScopedTypeRef(
-      __unsafe_unretained T object = Traits::InvalidValue(),
+      GN_SCOPED_UNRETAINED T object = Traits::InvalidValue(),
       base::scoped_policy::OwnershipPolicy policy = base::scoped_policy::ASSUME)
       : object_(object) {
     if (object_ && policy == base::scoped_policy::RETAIN)
@@ -96,7 +106,7 @@
     return &object_;
   }
 
-  void reset(__unsafe_unretained T object = Traits::InvalidValue(),
+  void reset(GN_SCOPED_UNRETAINED T object = Traits::InvalidValue(),
              base::scoped_policy::OwnershipPolicy policy =
                  base::scoped_policy::ASSUME) {
     if (object && policy == base::scoped_policy::RETAIN)
@@ -106,16 +116,16 @@
     object_ = object;
   }
 
-  bool operator==(__unsafe_unretained T that) const { return object_ == that; }
+  bool operator==(GN_SCOPED_UNRETAINED T that) const { return object_ == that; }
 
-  bool operator!=(__unsafe_unretained T that) const { return object_ != that; }
+  bool operator!=(GN_SCOPED_UNRETAINED T that) const { return object_ != that; }
 
-  operator T() const __attribute((ns_returns_not_retained)) { return object_; }
+  operator T() const GN_SCOPED_NOT_RETAINED { return object_; }
 
-  T get() const __attribute((ns_returns_not_retained)) { return object_; }
+  T get() const GN_SCOPED_NOT_RETAINED { return object_; }
 
   void swap(ScopedTypeRef& that) {
-    __unsafe_unretained T temp = that.object_;
+    GN_SCOPED_UNRETAINED T temp = that.object_;
     that.object_ = object_;
     object_ = temp;
   }
@@ -123,16 +133,19 @@
   // ScopedTypeRef<>::release() is like std::unique_ptr<>::release.  It is NOT
   // a wrapper for Release().  To force a ScopedTypeRef<> object to call
   // Release(), use ScopedTypeRef<>::reset().
-  [[nodiscard]] T release() __attribute((ns_returns_not_retained)) {
-    __unsafe_unretained T temp = object_;
+  [[nodiscard]] T release() GN_SCOPED_NOT_RETAINED {
+    GN_SCOPED_UNRETAINED T temp = object_;
     object_ = Traits::InvalidValue();
     return temp;
   }
 
  private:
-  __unsafe_unretained T object_;
+  GN_SCOPED_UNRETAINED T object_;
 };
 
 }  // namespace base
 
+#undef GN_SCOPED_NOT_RETAINED
+#undef GN_SCOPED_UNRETAINED
+
 #endif  // BASE_MAC_SCOPED_TYPEREF_H_
