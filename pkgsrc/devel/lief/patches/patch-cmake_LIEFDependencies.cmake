$NetBSD$

The external spdlog target supplies its include directories. Keep build
directories out of the installed CMake targets.

--- cmake/LIEFDependencies.cmake.orig
+++ cmake/LIEFDependencies.cmake
@@ -176,8 +176,6 @@
   find_package(spdlog 1.17.0 REQUIRED)
   list(APPEND CMAKE_MODULE_PATH "${SPDLOG_DIR}/cmake")
   target_link_libraries(lief_spdlog INTERFACE spdlog::spdlog)
-  get_target_property(SPDLOG_INC_DIR spdlog::spdlog INTERFACE_INCLUDE_DIRECTORIES)
-  target_include_directories(lief_spdlog SYSTEM INTERFACE ${SPDLOG_INC_DIR})
 else()
   set(SPDLOG_VERSION 1.17.0)
   set(SPDLOG_SHA256 SHA256=b11912a82d149792fef33fabd0503b13d54aeac25c1464755461d4108ea71fc2)
