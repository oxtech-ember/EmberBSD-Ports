# Compatibility name for the single installed minizip-ng implementation.
include(CMakeFindDependencyMacro)
find_dependency(minizip-ng CONFIG)
if(NOT TARGET MINIZIP::minizip)
  get_filename_component(_minizip_prefix "${CMAKE_CURRENT_LIST_DIR}/../../.." ABSOLUTE)
  add_library(MINIZIP::minizip INTERFACE IMPORTED)
  set_target_properties(MINIZIP::minizip PROPERTIES
    INTERFACE_INCLUDE_DIRECTORIES "${_minizip_prefix}/include"
    INTERFACE_LINK_LIBRARIES MINIZIP::minizip-ng)
  unset(_minizip_prefix)
endif()
