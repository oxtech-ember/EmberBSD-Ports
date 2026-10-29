$NetBSD$

Origin: EmberBSD contributors (AI-assisted).
Bound numeric formatting and reject truncation in the jsonx example.
--- example/jsonx/jsonx.cpp
+++ example/jsonx/jsonx.cpp
@@ -34,27 +34,32 @@
     
     bool Int(int i) {
         char buffer[12];
-        return WriteNumberElement(buffer, sprintf(buffer, "%d", i));
+        int length = snprintf(buffer, sizeof(buffer), "%d", i);
+        return WriteNumberElement(buffer, sizeof(buffer), length);
     }
     
     bool Uint(unsigned i) {
         char buffer[11];
-        return WriteNumberElement(buffer, sprintf(buffer, "%u", i));
+        int length = snprintf(buffer, sizeof(buffer), "%u", i);
+        return WriteNumberElement(buffer, sizeof(buffer), length);
     }
     
     bool Int64(int64_t i) {
         char buffer[21];
-        return WriteNumberElement(buffer, sprintf(buffer, "%" PRId64, i));
+        int length = snprintf(buffer, sizeof(buffer), "%" PRId64, i);
+        return WriteNumberElement(buffer, sizeof(buffer), length);
     }
     
     bool Uint64(uint64_t i) {
         char buffer[21];
-        return WriteNumberElement(buffer, sprintf(buffer, "%" PRIu64, i));
+        int length = snprintf(buffer, sizeof(buffer), "%" PRIu64, i);
+        return WriteNumberElement(buffer, sizeof(buffer), length);
     }
     
     bool Double(double d) {
         char buffer[30];
-        return WriteNumberElement(buffer, sprintf(buffer, "%.17g", d));
+        int length = snprintf(buffer, sizeof(buffer), "%.17g", d);
+        return WriteNumberElement(buffer, sizeof(buffer), length);
     }
 
     bool RawNumber(const char* str, SizeType length, bool) {
@@ -172,7 +177,9 @@
         return true;
     }
 
-    bool WriteNumberElement(const char* buffer, int length) {
+    bool WriteNumberElement(const char* buffer, size_t capacity, int length) {
+        if (length < 0 || static_cast<size_t>(length) >= capacity)
+            return false;
         if (!WriteStartElement("number"))
             return false;
         for (int j = 0; j < length; j++)
