if(NOT TARGET LibPopcnt::libpopcnt)
  add_library(LibPopcnt::libpopcnt INTERFACE IMPORTED)
  get_filename_component(_libpopcnt_prefix "${CMAKE_CURRENT_LIST_DIR}/../../.." ABSOLUTE)
  set_target_properties(LibPopcnt::libpopcnt PROPERTIES
    INTERFACE_INCLUDE_DIRECTORIES "${_libpopcnt_prefix}/include")
endif()
