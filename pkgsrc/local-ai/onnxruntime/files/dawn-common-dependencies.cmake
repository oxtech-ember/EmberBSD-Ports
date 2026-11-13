# Dawn expects unnamespaced SPIRV-Headers; use the shared pkgsrc target.
find_package(VulkanHeaders CONFIG REQUIRED)
find_package(VulkanUtilityLibraries 1.4.363 CONFIG REQUIRED)
find_package(SPIRV-Headers CONFIG REQUIRED)
if(NOT TARGET SPIRV-Headers)
  add_library(SPIRV-Headers ALIAS SPIRV-Headers::SPIRV-Headers)
endif()

# SPIRV-Tools configures even when excluded from the selected plugin target.
# Its external/CMakeLists.txt expects the header source root explicitly.
if(NOT DAWN_SPIRV_HEADERS_DIR OR NOT IS_DIRECTORY "${DAWN_SPIRV_HEADERS_DIR}/include/spirv")
  message(FATAL_ERROR "DAWN_SPIRV_HEADERS_DIR must name the shared buildlink prefix")
endif()
set(SPIRV-Headers_SOURCE_DIR "${DAWN_SPIRV_HEADERS_DIR}")
