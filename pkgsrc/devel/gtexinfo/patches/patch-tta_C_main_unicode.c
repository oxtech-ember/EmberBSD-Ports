$NetBSD$

Pass ucs4_t code points as the unsigned long that %lx and %lX read.
On LP64 the upper half was otherwise undefined, so node identifiers
could differ between a node and its references.

--- tta/C/main/unicode.c.orig
+++ tta/C/main/unicode.c
@@ -291,13 +291,14 @@
       u8_next (&first_char, encoded_u8);
       free (encoded_u8);
       if (first_char < 127)
-        xasprintf (&new_eight_bit, "%02lX", first_char);
+        xasprintf (&new_eight_bit, "%02lX", (unsigned long) first_char);
       else
         {
           char *codepoint;
           if (first_char <= 0xFFFF)
             {
-              xasprintf (&codepoint, "%04lX", first_char);
+              xasprintf (&codepoint, "%04lX",
+                         (unsigned long) first_char);
               const char *found = (const char *)bsearch (&codepoint,
                              unicode_to_eight_bit[encoding_index].codepoints,
                              unicode_to_eight_bit[encoding_index].number,
