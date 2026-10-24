$NetBSD$

Pass ucs4_t code points as the unsigned long that %lx and %lX read.
On LP64 the upper half was otherwise undefined, so node identifiers
could differ between a node and its references.

--- tta/C/convert/format_html.c.orig
+++ tta/C/convert/format_html.c
@@ -7111,7 +7111,8 @@
           uint8_t *encoded_u8 = utf8_from_string (normalized_accent_text);
           ucs4_t first_char;
           const uint8_t *next = u8_next (&first_char, encoded_u8);
-          text_printf (&accented_text, "\\%04lX ", first_char);
+          text_printf (&accented_text, "\\%04lX ",
+                       (unsigned long) first_char);
           next_text = string_from_utf8 (next);
           free (encoded_u8);
           text_append (&accented_text, next_text);
