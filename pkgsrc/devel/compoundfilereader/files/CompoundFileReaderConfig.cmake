if(NOT TARGET CompoundFileReader::CompoundFileReader)
  get_filename_component(_CompoundFileReader_PREFIX "${CMAKE_CURRENT_LIST_DIR}/../../../" ABSOLUTE)
  add_library(CompoundFileReader::CompoundFileReader INTERFACE IMPORTED)
  set_target_properties(CompoundFileReader::CompoundFileReader PROPERTIES
    INTERFACE_INCLUDE_DIRECTORIES "${_CompoundFileReader_PREFIX}/include"
    INTERFACE_COMPILE_FEATURES cxx_std_11)
  unset(_CompoundFileReader_PREFIX)
endif()
