$NetBSD$

Pass the ctype argument of chew.c as unsigned char, as the other ctype calls
of the file do. On NetBSD and EmberBSD isspace is an array-indexing macro;
clang -Wchar-subscripts with the build-host -Werror stopped the Binutils
build there.

Origin: EmberBSD (AI-assisted). Not submitted upstream.

--- bfd/doc/chew.c.orig
+++ bfd/doc/chew.c
@@ -940,7 +940,7 @@
   for (idx = 0; at (tos, idx) != 0; ++idx)
     {
       char c = at (tos, idx);
-      if (isspace (c))
+      if (isspace ((unsigned char) c))
 	{
 	  if (!last_was_ws)
 	    {
