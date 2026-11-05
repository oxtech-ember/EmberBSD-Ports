if(NOT TARGET BS::thread_pool)
  add_library(BS::thread_pool INTERFACE IMPORTED)
  get_filename_component(_bs_thread_pool_prefix "${CMAKE_CURRENT_LIST_DIR}/../../.." ABSOLUTE)
  set_target_properties(BS::thread_pool PROPERTIES
    INTERFACE_INCLUDE_DIRECTORIES "${_bs_thread_pool_prefix}/include"
    INTERFACE_COMPILE_FEATURES cxx_std_17)
endif()
