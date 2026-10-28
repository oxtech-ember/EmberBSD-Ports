Use current gnulib pointer alignment arithmetic.
Source: https://github.com/coreutils/gnulib/blob/5df606bbd0ef54a8f150c3303c870b9381a661f0/lib/obstack.in.h

--- lib/obstack.h.orig
+++ lib/obstack.h
@@ -129,22 +129,23 @@
 # define _OBSTACK_CAST(type, expr) (expr)
 #endif
 
-/* If B is the base of an object addressed by P, return the result of
-   aligning P to the next multiple of A + 1.  B and P must be of type
-   char *.  A + 1 must be a power of 2.  */
-
-#define __BPTR_ALIGN(B, P, A) ((B) + (((P) - (B) + (A)) & ~(A)))
-
-/* Similar to __BPTR_ALIGN (B, P, A), except optimize the common case
-   where pointers can be converted to integers, aligned as integers,
-   and converted back again.  If ptrdiff_t is narrower than a
-   pointer (e.g., the AS/400), play it safe and compute the alignment
-   relative to B.  Otherwise, use the faster strategy of computing the
-   alignment relative to 0.  */
+/* An integer type wide enough to hold a pointer, if available.  */
+#ifdef __UINTPTR_TYPE__
+# define _OBSTACK_UINTPTR_TYPE __UINTPTR_TYPE__
+#elif defined __STDC_VERSION__ && 199901L <= __STDC_VERSION__
+# include <stdint.h>
+# ifdef UINTPTR_MAX
+#  define _OBSTACK_UINTPTR_TYPE uintptr_t
+# endif
+#endif
 
-#define __PTR_ALIGN(B, P, A)						      \
-  __BPTR_ALIGN (sizeof (ptrdiff_t) < sizeof (void *) ? (B) : (char *) 0,      \
-                P, A)
+/* Align P to the next multiple of A + 1, using base B when no
+   pointer-width integer type is available.  A + 1 must be a power of 2.  */
+#ifndef _OBSTACK_UINTPTR_TYPE
+# define __PTR_ALIGN(B, P, A) ((B) + (((P) - (B) + (A)) & ~(A)))
+#else
+# define __PTR_ALIGN(B, P, A) ((P) + ((- (_OBSTACK_UINTPTR_TYPE) (P)) & (A)))
+#endif
 
 #ifndef __attribute_pure__
 # define __attribute_pure__ _GL_ATTRIBUTE_PURE
