$NetBSD$

Keep both set bits inside the word during both Bit Spread walks.
The upstream loop shifts by UL_LEN and UL_LEN + 1 at each turnaround.
C does not define these shifts. Preserve the two-bit pattern and its
complement, including both endpoints, instead of wrapping the high bit.

Origin: EmberBSD, AI-assisted by OpenAI Codex (GPT-6); not submitted upstream.
Upstream: memtester 4.7.1, tests.c (GPL-2.0-only).

--- tests.c.orig	2024-12-16 17:32:28.000000000 +0000
+++ tests.c
@@ -388,23 +388,23 @@
 
     printf("           ");
     fflush(stdout);
-    for (j = 0; j < UL_LEN * 2; j++) {
+    for (j = 0; j < (UL_LEN - 2) * 2; j++) {
         printf("\b\b\b\b\b\b\b\b\b\b\b");
         p1 = (ulv *) bufa;
         p2 = (ulv *) bufb;
         printf("setting %3u", j);
         fflush(stdout);
         for (i = 0; i < count; i++) {
-            if (j < UL_LEN) { /* Walk it up. */
+            if (j < UL_LEN - 2) { /* Walk it up. */
                 *p1++ = *p2++ = (i % 2 == 0)
                     ? (ONE << j) | (ONE << (j + 2))
                     : UL_ONEBITS ^ ((ONE << j)
                                     | (ONE << (j + 2)));
             } else { /* Walk it back down. */
                 *p1++ = *p2++ = (i % 2 == 0)
-                    ? (ONE << (UL_LEN * 2 - 1 - j)) | (ONE << (UL_LEN * 2 + 1 - j))
-                    : UL_ONEBITS ^ (ONE << (UL_LEN * 2 - 1 - j)
-                                    | (ONE << (UL_LEN * 2 + 1 - j)));
+                    ? (ONE << (UL_LEN * 2 - 5 - j)) | (ONE << (UL_LEN * 2 - 3 - j))
+                    : UL_ONEBITS ^ (ONE << (UL_LEN * 2 - 5 - j)
+                                    | (ONE << (UL_LEN * 2 - 3 - j)));
             }
         }
         printf("\b\b\b\b\b\b\b\b\b\b\b");
