$NetBSD$

--- a/tools/imagetool.h
+++ b/tools/imagetool.h
@@ -290,7 +290,7 @@
 	} while (0)
 #define SECTION(name)   __attribute__((section("__DATA, " #name)))
 
-struct image_type_params **__start_image_type, **__stop_image_type;
+extern struct image_type_params **__start_image_type, **__stop_image_type;
 #else
 #define INIT_SECTION(name) /* no-op for ELF */
 #define SECTION(name)   __attribute__((section(#name)))
