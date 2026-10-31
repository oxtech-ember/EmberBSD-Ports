$NetBSD$

Limit the availability check's -Werror to the check itself, preserving
compiler warning policy for the rest of the build.

--- cmake/Findfutimens.cmake.orig
+++ cmake/Findfutimens.cmake
@@ -1,4 +1,4 @@
-include(EnableWarnings)
+include(CMakePushCheckState)
 
 if(APPLE)
 	# We cannot simply CHECK_FUNCTION_EXISTS on macOS because
@@ -6,9 +6,10 @@ if(APPLE)
 	# that doesn't have futimens.  Instead we need to enable warnings
 	# as errors, then check for the symbol existing in `sys/stat.h`,
 	# then reset warnings as errors.
-	enable_warnings(error)
+	cmake_push_check_state()
+	set(CMAKE_REQUIRED_FLAGS "${CMAKE_REQUIRED_FLAGS} -Werror")
 	check_symbol_exists(futimens sys/stat.h HAVE_FUTIMENS)
-	disable_warnings(error)
+	cmake_pop_check_state()
 else()
 	check_function_exists(futimens HAVE_FUTIMENS)
 endif()
