set(emberbsd-backend_SRCS
    EmberBSDBackend.cpp
    EmberBSDResource.cpp
    EmberUpdateState.cpp
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

kcoreaddons_add_plugin(EmberBSDNotifier SOURCES EmberBSDNotifier.cpp EmberUpdateState.cpp INSTALL_NAMESPACE "discover-notifier")
target_link_libraries(EmberBSDNotifier Discover::Notifiers KF6::I18n)
set_target_properties(EmberBSDNotifier PROPERTIES INSTALL_RPATH ${CMAKE_INSTALL_FULL_LIBDIR}/plasma-discover)

install(FILES emberbsd-categories.xml
    DESTINATION ${KDE_INSTALL_DATADIR}/libdiscover/categories
    RENAME emberbsd-backend-categories.xml)
install(FILES org.emberbsd.discover.install.policy org.emberbsd.discover.update.policy
    DESTINATION ${KDE_INSTALL_DATADIR}/polkit-1/actions)
