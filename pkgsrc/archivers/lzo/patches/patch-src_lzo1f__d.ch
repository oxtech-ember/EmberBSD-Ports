$NetBSD$

Fix the upstream-documented one-byte overread in the LZO1F safe decoder.
Origin: https://www.oberhumer.com/opensource/lzo/ (upstream patch by
XananasX7 and David Korczynski, Ada Logics). Packaging is AI-assisted.

--- src/lzo1f_d.ch.orig
+++ src/lzo1f_d.ch
@@ -58,8 +58,10 @@ DO_DECOMPRESS  ( const lzo_bytep in , lzo_uint in_len,
     while (TEST_IP_AND_TEST_OP)
     {
         t = *ip++;
-        if (t > 31)
+        if (t > 31) {
+            NEED_IP(1);
             goto match;
+        }
 
         /* a literal run */
         if (t == 0)
