$NetBSD$

Adapt the upstream gnulib sanitizer-safe bytewise path to grep 3.12.
Production optimization remains unchanged. Origin: gnulib commits
f6b3efe5018211f371305e693c8d786d9489a769,
09d5e8a0737510d2778f333a425288dc00219858 and
261efbba928fbad24334f218b5c3190653bcec18; EmberBSD adaptation AI-assisted.

--- lib/rawmemchr.c.orig	2026-10-28 22:14:21
+++ lib/rawmemchr.c	2026-10-28 22:14:33
@@ -41,13 +41,24 @@
                            - __builtin_cheri_offset_get (s)));
 # else
 
+  unsigned char c = c_in;
+
+  /* As in current gnulib, use bytewise reads when memory sanitizers are
+     enabled; the word-at-a-time production path can cross object bounds. */
+#  if defined __has_feature
+#   if __has_feature (address_sanitizer) || __has_feature (hwaddress_sanitizer) || __has_feature (memory_sanitizer)
+#    define GREP_RAWMEMCHR_SANITIZED 1
+#   endif
+#  endif
+#  if !defined __SANITIZE_ADDRESS__ && !defined __SANITIZE_HWADDRESS__ \
+      && !defined __SANITIZE_MEMORY__ && !defined GREP_RAWMEMCHR_SANITIZED
+  {
   /* You can change this typedef to experiment with performance.  */
   typedef uintptr_t longword;
   /* Verify that the longword type lacks padding bits.  */
   static_assert (UINTPTR_WIDTH == UCHAR_WIDTH * sizeof (uintptr_t));
 
   const unsigned char *char_ptr;
-  unsigned char c = c_in;
 
   /* Handle the first few bytes by reading one byte at a time.
      Do this until CHAR_PTR is aligned on a natural longword boundary,
@@ -117,7 +128,7 @@
       longword_ptr++;
     }
 
-  char_ptr = s = longword_ptr;
+  s = longword_ptr;
 
   /* At this point, we know that one of the sizeof (longword) bytes
      starting at char_ptr is == c.  If we knew endianness, we
@@ -125,7 +136,10 @@
      accesses, just by looking at the tmp result from the last loop
      iteration.  However, the following simple and portable code does
      not attempt this potential optimization.  */
+  }
+#  endif
 
+  const unsigned char *char_ptr = s;
   while (*char_ptr != c)
     char_ptr++;
   return (void *) char_ptr;
