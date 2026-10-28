$NetBSD$

Origin: EmberBSD contributors (AI-assisted); not submitted upstream.
Include the standard declarations used by the test formatting helpers.

--- src/gtest/include/mesa-gtest-extras.h.orig
+++ src/gtest/include/mesa-gtest-extras.h
@@ -24,6 +24,7 @@
 #ifndef MESA_GTEST_EXTRAS_H
 #define MESA_GTEST_EXTRAS_H
 
+#include <iomanip>
 #include <gtest/gtest.h>
 
 template <typename T>
