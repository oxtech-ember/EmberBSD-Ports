include(CMakeFindDependencyMacro)
find_dependency(ZLIB)
if(NOT TARGET gzip-hpp::gzip-hpp)
  get_filename_component(_gzip_hpp_PREFIX "${CMAKE_CURRENT_LIST_DIR}/../../../" ABSOLUTE)
  add_library(gzip-hpp::gzip-hpp INTERFACE IMPORTED)
  set_target_properties(gzip-hpp::gzip-hpp PROPERTIES
    INTERFACE_INCLUDE_DIRECTORIES "${_gzip_hpp_PREFIX}/include"
    INTERFACE_LINK_LIBRARIES ZLIB::ZLIB
    INTERFACE_COMPILE_FEATURES cxx_std_11)
  unset(_gzip_hpp_PREFIX)
endif()
