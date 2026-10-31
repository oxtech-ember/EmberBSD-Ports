$NetBSD$

Build with the common Git xdiff source and libgit2 adapter.

--- cmake/SelectXdiff.cmake.orig
+++ cmake/SelectXdiff.cmake
@@ -1,9 +1,9 @@
-# Optional external dependency: xdiff
-if(USE_XDIFF STREQUAL "system")
-	message(FATAL_ERROR "external/system xdiff is not yet supported")
-else()
-	add_subdirectory("${PROJECT_SOURCE_DIR}/deps/xdiff" "${PROJECT_BINARY_DIR}/deps/xdiff")
-	list(APPEND LIBGIT2_DEPENDENCY_INCLUDES "${PROJECT_SOURCE_DIR}/deps/xdiff")
-	list(APPEND LIBGIT2_DEPENDENCY_OBJECTS "$<TARGET_OBJECTS:xdiff>")
-	add_feature_info(xdiff ON "xdiff support (bundled)")
+# Build against the prepared, shared Git xdiff source.
+if(NOT XDIFF_SOURCE_DIR OR NOT EXISTS "${XDIFF_SOURCE_DIR}/xdiff.h")
+	message(FATAL_ERROR "the shared Git xdiff source is required")
 endif()
+
+add_subdirectory("${PROJECT_SOURCE_DIR}/deps/xdiff" "${PROJECT_BINARY_DIR}/deps/xdiff")
+list(APPEND LIBGIT2_DEPENDENCY_INCLUDES "${XDIFF_SOURCE_DIR}" "${PROJECT_SOURCE_DIR}/deps/xdiff")
+list(APPEND LIBGIT2_DEPENDENCY_OBJECTS "$<TARGET_OBJECTS:xdiff>")
+add_feature_info(xdiff ON "xdiff support (shared Git source)")
