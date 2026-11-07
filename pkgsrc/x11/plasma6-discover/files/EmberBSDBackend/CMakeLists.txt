set(emberbsd-backend_SRCS
    EmberBSDBackend.cpp
    EmberBSDResource.cpp
)

kcoreaddons_add_plugin(emberbsd-backend SOURCES ${emberbsd-backend_SRCS} INSTALL_NAMESPACE "discover")
target_link_libraries(emberbsd-backend
    Qt::Core
    KF6::CoreAddons
    Discover::Common
)
set_target_properties(emberbsd-backend PROPERTIES
    INSTALL_RPATH ${CMAKE_INSTALL_FULL_LIBDIR}/plasma-discover
)

install(FILES emberbsd-categories.xml DESTINATION ${KDE_INSTALL_DATADIR}/libdiscover/categories)
