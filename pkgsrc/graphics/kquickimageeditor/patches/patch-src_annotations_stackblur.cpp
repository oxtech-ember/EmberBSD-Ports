$NetBSD$

Compile the blur with Highway's portable target. The cross compiler does
not enable the x86 features that the dynamic targets require.

--- src/annotations/stackblur.cpp.orig
+++ src/annotations/stackblur.cpp
@@ -8,6 +8,9 @@
 #include <QImage>
 #include <QtConcurrent/QtConcurrentMap>
 
+/* One translation unit cannot carry every Highway x86 target flag.
+ * The portable target is enough for the screenshot editor. */
+#define HWY_COMPILE_ONLY_EMU128
 #include <hwy/aligned_allocator.h>
 #include <hwy/base.h> // basic helper macros, typedefs, concepts and functions
 
