include(CMakeFindDependencyMacro)
find_dependency(LibPopcnt CONFIG)
include("${CMAKE_CURRENT_LIST_DIR}/sul-dynamic_bitset.cmake")
set_property(TARGET sul::dynamic_bitset APPEND PROPERTY
  INTERFACE_LINK_LIBRARIES LibPopcnt::libpopcnt)
