$NetBSD$

Keep float coordinate arithmetic and integer comparisons source-compatible.

--- litehtml/include/litehtml/pixel_type.h.orig
+++ litehtml/include/litehtml/pixel_type.h
@@ -26,7 +26,7 @@
         {
             return m_value;
         }
-        constexpr operator int() const
+        explicit constexpr operator int() const
         {
             return static_cast<int>(m_value);
         }
@@ -132,6 +132,10 @@
         {
             return m_value > other.m_value && std::abs(m_value - other.m_value) >= epsilon;
         }
+        constexpr bool operator>(int other) const
+        {
+            return *this > pixel_float_t(other);
+        }
         constexpr bool operator<=(pixel_float_t other) const
         {
             return *this < other || *this == other;
@@ -139,6 +143,10 @@
         constexpr bool operator>=(pixel_float_t other) const
         {
             return *this > other || *this == other;
+        }
+        constexpr bool operator>=(int other) const
+        {
+            return *this >= pixel_float_t(other);
         }
 
         // Unary - operator
@@ -250,6 +258,14 @@
     {
         return {a + b.value()};
     }
+    constexpr double operator+(double a, pixel_float_t b)
+    {
+        return a + b.value();
+    }
+    constexpr double operator+(pixel_float_t a, double b)
+    {
+        return a.value() + b;
+    }
     constexpr pixel_float_t operator+(int a, pixel_float_t b)
     {
         return {static_cast<float>(a) + b.value()};
@@ -257,6 +273,14 @@
     constexpr pixel_float_t operator-(float a, pixel_float_t b)
     {
         return {a - b.value()};
+    }
+    constexpr double operator-(double a, pixel_float_t b)
+    {
+        return a - b.value();
+    }
+    constexpr double operator-(pixel_float_t a, double b)
+    {
+        return a.value() - b;
     }
     constexpr pixel_float_t operator-(int a, pixel_float_t b)
     {
