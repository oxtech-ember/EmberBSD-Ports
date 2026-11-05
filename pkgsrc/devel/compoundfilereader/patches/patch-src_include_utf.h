$NetBSD$

# Carry KiCad's portable wide-string conversions and ODR-safe inline helper.
--- src/include/utf.h
+++ src/include/utf.h
@@ -49,7 +49,7 @@
     return true;
 }
 
-static int CodePointToUTF8(uint32_t cp, uint32_t* c1, uint32_t* c2, uint32_t* c3, uint32_t* c4)
+static inline int CodePointToUTF8(uint32_t cp, uint32_t* c1, uint32_t* c2, uint32_t* c3, uint32_t* c4)
 {
     if (cp < 0x80)
     {
@@ -102,36 +102,46 @@
 std::wstring UTF16ToWstring(const T* u16, size_t len = 0)
 {
     std::wstring ret;
-#ifdef _MSC_VER
-    while (*u16) ret += *u16++;
-#else
-    uint32_t cp;
-    size_t pos = 0;
-    while (GetNextCodePointFromUTF16(u16, len, &pos, &cp))
+    if( sizeof( wchar_t ) == 2 )
     {
-        ret += cp;
+        while( *u16 )
+            ret += *u16++;
     }
-#endif
+    else
+    {
+        uint32_t cp;
+        size_t   pos = 0;
+        while( GetNextCodePointFromUTF16( u16, len, &pos, &cp ) )
+        {
+            if( !cp )
+                break;
+
+            ret += cp;
+        }
+    }
     return ret;
 }
 
 template <typename T>
 std::string WstringToUTF8(const T* wstr)
 {
-#ifdef _MSC_VER
-    return UTF16ToUTF8(wstr);
-#else
-    std::string u8;
-    uint32_t cp;
-    while ((cp = *wstr++) != 0)
+    if( sizeof( wchar_t ) == 2 )
     {
-        uint32_t c[4];
-        int count = CodePointToUTF8(cp, c, c+1, c+2, c+3);
-        for (int i = 0; i < count; i++)
+        return UTF16ToUTF8( wstr );
+    }
+    else
+    {
+        std::string u8;
+        uint32_t    cp;
+        while( ( cp = *wstr++ ) != 0 )
         {
-            u8 += static_cast<char>(c[i]);
+            uint32_t c[4];
+            int      count = CodePointToUTF8( cp, c, c + 1, c + 2, c + 3 );
+            for( int i = 0; i < count; i++ )
+            {
+                u8 += static_cast<char>( c[i] );
+            }
         }
+        return u8;
     }
-    return u8;
-#endif
 }
