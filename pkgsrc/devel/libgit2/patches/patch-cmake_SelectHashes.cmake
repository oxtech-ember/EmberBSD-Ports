$NetBSD$

Use the shared SHA-1 collision detection provider.

--- cmake/SelectHashes.cmake.orig
+++ cmake/SelectHashes.cmake
@@ -24,6 +24,13 @@
 endif()
 
 if(USE_SHA1 STREQUAL "CollisionDetection")
+	find_pkglibraries(SHA1DETECTCOLL sha1detectcoll)
+	if(NOT SHA1DETECTCOLL_FOUND)
+		message(FATAL_ERROR "system sha1detectcoll is required")
+	endif()
+	list(APPEND LIBGIT2_SYSTEM_INCLUDES ${SHA1DETECTCOLL_INCLUDE_DIRS})
+	list(APPEND LIBGIT2_SYSTEM_LIBS ${SHA1DETECTCOLL_LIBRARIES})
+	list(APPEND LIBGIT2_PC_REQUIRES "sha1detectcoll")
 	set(GIT_SHA1_COLLISIONDETECT 1)
 elseif(USE_SHA1 STREQUAL "OpenSSL")
 	set(GIT_SHA1_OPENSSL 1)
