# Origin: EmberBSD (AI-assisted). Keep native Qt paths independent of layout.
# Installed Qt exposes this directory through qtpaths --query QT_INSTALL_LIBEXECS.
EMBERBSD_QT_HOST_LIBEXECS?= ${EMBERBSD_QT_HOST_PATH}/libexec
.if empty(EMBERBSD_QT_HOST_PATH:M/*) || \
    !exists(${EMBERBSD_QT_HOST_PATH}/lib/cmake/Qt6CoreTools/Qt6CoreToolsConfig.cmake) || \
    empty(EMBERBSD_QT_HOST_LIBEXECS:M/*) || \
    !exists(${EMBERBSD_QT_HOST_LIBEXECS}/moc)
PKG_FAIL_REASON+= "Select matching native Qt CMake metadata and moc with EMBERBSD_QT_HOST_PATH and EMBERBSD_QT_HOST_LIBEXECS"
.endif
