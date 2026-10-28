Allocate space for one limb even when the represented value has zero limbs.
This keeps the existing zero-limb representation and permits compilers to
check the size of the pointed-to object.

--- lib/vasnprintf.c.orig
+++ lib/vasnprintf.c
@@ -451,7 +451,7 @@
     {
       /* src1 or src2 is zero.  */
       dest->nlimbs = 0;
-      dest->limbs = (mp_limb_t *) malloc (1);
+      dest->limbs = (mp_limb_t *) malloc (sizeof *dest->limbs);
     }
   else
     {
