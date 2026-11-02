$NetBSD$

NetBSD has no <alloca.h>; it declares alloca() in <stdlib.h>, which
SDL_stdinc.h includes. Without HAVE_ALLOCA_H, SDL_stdinc.h uses the
compiler builtin when alloca is not already a macro.

--- include/SDL2/SDL_config_unix.h.cmake.orig
+++ include/SDL2/SDL_config_unix.h.cmake
@@ -169,7 +169,9 @@
 
 /* Non-standardized headers, but we assume they exist anyway
  * (please report a bug if your Unix platform doesn't have these) */
+#if !defined(__NetBSD__) /* NetBSD declares alloca() in <stdlib.h> */
 #define HAVE_ALLOCA_H 1
+#endif
 #define HAVE_MALLOC_H 1
 #define HAVE_MEMORY_H 1
 
