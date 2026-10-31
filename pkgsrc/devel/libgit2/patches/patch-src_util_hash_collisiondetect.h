$NetBSD$

Use the shared SHA-1 collision detection provider.

--- src/util/hash/collisiondetect.h.orig
+++ src/util/hash/collisiondetect.h
@@ -10,7 +10,8 @@
 
 #include "hash/sha.h"
 
-#include "sha1dc/sha1.h"
+#include <stddef.h>
+#include <sha1dc/sha1.h>
 
 struct git_hash_sha1_ctx {
 	SHA1_CTX c;
