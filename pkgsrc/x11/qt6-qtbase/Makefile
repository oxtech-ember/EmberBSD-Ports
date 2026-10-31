# $NetBSD: Makefile,v 1.77 2026/09/08 20:34:46 markd Exp $

DISTNAME=	qtbase-everywhere-src-${QTVERSION}
PKGNAME=	qt6-qtbase-${QTVERSION}
PKGREVISION=	14
COMMENT=	C++ X GUI toolkit
CATEGORIES=	x11

LICENSE=	gnu-lgpl-v3 OR gnu-gpl-v2 OR gnu-gpl-v3

CONFLICTS+=	qt6-qtwayland<6.10.0

.include "Makefile.common"

PLIST_VARS+=	bsdfb
.if ${OPSYS} == "NetBSD"
PLIST.bsdfb=	yes
.endif

.if defined(EMBERBSD_QTBASE_DEVEL)
.if ${EMBERBSD_QTBASE_DEVEL} != "yes" || ${PKGPATH} != "x11/qt6-qtbase-devel"
PKG_FAIL_REASON+= "The Qtbase SDK role belongs to x11/qt6-qtbase-devel"
.endif
PKGNAME= qt6-qtbase-devel-${QTVERSION}
COMMENT= Qtbase target SDK for the development-host sysroot
.if ${USE_CROSS_COMPILE:Uno:tl} != "yes" || ${OPSYS} != "NetBSD"
PKG_FAIL_REASON+= "The separate Qtbase SDK requires a NetBSD cross build; native Qtbase retains its full package"
.endif
.endif
.if ${USE_CROSS_COMPILE:Uno:tl} == "yes" && ${OPSYS} == "NetBSD"
.if ${MACHINE_ARCH} != "aarch64" && ${MACHINE_ARCH} != "x86_64"
PKG_FAIL_REASON+= "The Qtbase runtime/SDK split requires the common aarch64 or amd64 cross target"
.endif
PKGREVISION= 7
QTBASE_FULL_PLIST_SRC= ${EMBERBSD_QTBASE_PKGDIR}/PLIST.NetBSD ${EMBERBSD_QTBASE_PKGDIR}/PLIST
QTBASE_RUNTIME_PLIST_SRC= ${EMBERBSD_QTBASE_PKGDIR}/PLIST.runtime
QTBASE_DEVEL_PLIST_SRC= ${EMBERBSD_QTBASE_PKGDIR}/PLIST.NetBSD ${EMBERBSD_QTBASE_PKGDIR}/../qt6-qtbase-devel/PLIST
.if defined(EMBERBSD_QTBASE_DEVEL)
PKGREVISION= 9
.if ${PKGREVISION} != 9
PKG_FAIL_REASON+= "The Qtbase SDK requires package revision 9"
.endif
QTBASE_PACKAGE_PART= devel
.if ${QTBASE_PACKAGE_PART} != "devel"
PKG_FAIL_REASON+= "The Qtbase SDK recipe must select the devel partition"
.endif
PLIST_SRC= ${QTBASE_DEVEL_PLIST_SRC}
DEPENDS+= qt6-qtbase-${QTVERSION}nb7:../../x11/qt6-qtbase
CONFLICTS+= qt6-qtbase<${QTVERSION}nb7
.else
.if ${PKGREVISION} != 7
PKG_FAIL_REASON+= "The Qtbase runtime requires package revision 7"
.endif
QTBASE_PACKAGE_PART= runtime
.if ${QTBASE_PACKAGE_PART} != "runtime"
PKG_FAIL_REASON+= "The Qtbase runtime recipe must select the runtime partition"
.endif
PLIST_SRC= ${QTBASE_RUNTIME_PLIST_SRC}
.endif
.endif

HAS_CONFIGURE=		yes
CONFIGURE_ARGS+=	-prefix "${QTPREFIX}"
CONFIGURE_ARGS+=	-I "${PREFIX}/include"
CONFIGURE_ARGS+=	-L "${PREFIX}/lib"
CONFIGURE_ARGS+=	-cmake-use-default-generator
CONFIGURE_ARGS+=	-opensource -confirm-license
CONFIGURE_ARGS+=	-sysconfdir "${PKG_SYSCONFDIR}/xdg"
CONFIGURE_ARGS+=	-accessibility
CONFIGURE_ARGS+=	-icu
CONFIGURE_ARGS+=	-libproxy
CONFIGURE_ARGS+=	-openssl-linked
CONFIGURE_ARGS+=	-nomake examples
CONFIGURE_ARGS+=	-nomake tests
CONFIGURE_ARGS+=	-no-pch
CONFIGURE_ARGS+=	-no-sql-db2
CONFIGURE_ARGS+=	-no-sql-ibase
CONFIGURE_ARGS+=	-no-sql-mysql
CONFIGURE_ARGS+=	-no-sql-oci
CONFIGURE_ARGS+=	-no-sql-odbc
CONFIGURE_ARGS+=	-no-sql-psql
CONFIGURE_ARGS+=	-no-strip
CONFIGURE_ARGS+=	-no-tslib
CONFIGURE_ARGS+=	-no-use-gold-linker
CONFIGURE_ARGS+=	-pkg-config
CONFIGURE_ARGS+=	-qt-publicsuffix
CONFIGURE_ARGS+=	-release
CONFIGURE_ARGS+=	-shared
CONFIGURE_ARGS+=	-system-doubleconversion
CONFIGURE_ARGS+=	-system-harfbuzz
CONFIGURE_ARGS+=	-system-libjpeg
CONFIGURE_ARGS+=	-system-libmd4c
CONFIGURE_ARGS+=	-system-libpng
CONFIGURE_ARGS+=	-system-pcre
CONFIGURE_ARGS+=	-system-sqlite
CONFIGURE_ARGS+=	-system-zlib
CONFIGURE_ARGS+=	-avoid_cmake_archiving_api
CONFIGURE_ARGS+=	-no-bundled-xcb-xinput

PREFER.openssl=	pkgsrc

# Keep target script dependencies separate from executable build-host tools.
# pkgsrc rejects :run tools in a Darwin-to-NetBSD cross build.
USE_TOOLS+=		bash:build pkg-config
DEPENDS+=		bash-[0-9]*:../../shells/bash

.include "../../mk/bsd.prefs.mk"
.if ${OPSYS} == "Darwin" && ${USE_CROSS_COMPILE:Uno:tl} != "yes" && \
    ${EMBERBSD_NATIVE_CXX_ABI_NAMESPACE:U} == "__ember1"
DEPENDS+= libcxx>=23.1.4nb1:../../lang/libcxx
BUILD_DEFS+= EMBERBSD_NATIVE_CXX_ABI_NAMESPACE
.endif

.if ${OPSYS} != "Darwin"
CONFIGURE_ARGS+=	-fontconfig
QMAKE_CONF=		qmake.conf
.  if ${OPSYS} != "SunOS" && \
      (${MACHINE_ARCH} == "i386" || ${MACHINE_ARCH} == "x86_64")
CONFIGURE_ARGS+=	-reduce-relocations
.  endif
.else
CONFIGURE_ARGS+=	-no-vulkan	# needs MoltenVK on macOS
CONFIGURE_ARGS+=	-no-rpath	# avoid @rpath in dylibs
QMAKE_CONF=		qmake.conf.mac
.endif

# Qt's deployment helpers are host tools and are disabled in cross builds.
PLIST_VARS+=	androidtools targetmetadata egl egldevice wayland x11
.if ${USE_CROSS_COMPILE:Uno:tl} != "yes"
PLIST.androidtools=	yes
.endif

.include "../../mk/compiler.mk"

.if ${OPSYS} == "DragonFly"
CONFIGURE_ARGS+=		-platform freebsd-g++
LDFLAGS+=			-lexecinfo
.elif ${OPSYS} == "Darwin"
CONFIGURE_ARGS+=		-platform macx-clang
CONFIGURE_ARGS+=		-no-framework
# pkgsrc has a patch to avoid using SDK, but the configure
# logic gets confused if it can't find the header files
# so give it a direct path to them if they aren't installed
# in /usr/include
.  if !exists(/usr/include)
CONFIGURE_ARGS+=		-I ${OSX_SDK_PATH}/usr/include
.  endif
.  if exists(/usr/lib/libresolv.dylib)
LDFLAGS+=			-lresolv
.  endif
# -lexecinfo is bundled in libc
.  if exists(${OSX_SDK_PATH}/usr/include/execinfo.h)
BUILDLINK_TRANSFORM+=		rm:-lexecinfo
.  endif
.elif ${OPSYS} == "Linux"
LDFLAGS+=			-ldl
.elif ${OPSYS} == "NetBSD" || ${OPSYS} == "FreeBSD"
.  if exists(/usr/lib/libexecinfo.so)
LDFLAGS+=			-lexecinfo
.  endif
LDFLAGS.FreeBSD+=		-lutil
.elif ${OPSYS} == "SunOS"
CONFIGURE_ARGS+=		-no-inotify
.endif

#
# Qt uses FP16 intrinsics, but GCC isn't inserting libgcc due to it being in
# a shared library.  This isn't ideal but adding it via the usual variables
# is proving to be difficult as they are placed before the object files.
#
.if ${OPSYS} == "SunOS"
CWRAPPERS_APPEND.cc+=	-lgcc
CWRAPPERS_APPEND.cxx+=	-lgcc
.endif

REPLACE_PYTHON+=	util/testrunner/sanitizer-testrunner.py
REPLACE_PYTHON+=	util/testrunner/qt-testrunner.py

PTHREAD_OPTS+=		require
UNLIMIT_RESOURCES=	datasize

BUILDLINK_PASSTHRU_DIRS+=	${QTPREFIX}

CHECK_INTERPRETER_SKIP+=	qt6/libexec/qt-android-runner.py
CHECK_INTERPRETER_SKIP+=	qt6/mkspecs/features/data/mac/objc_namespace.sh
CHECK_INTERPRETER_SKIP+=	qt6/mkspecs/features/uikit/device_destinations.sh
CHECK_INTERPRETER_SKIP+=	qt6/mkspecs/features/uikit/devices.py

SUBST_CLASSES+=		opt
SUBST_STAGE.opt=	pre-configure
SUBST_MESSAGE.opt=	Removing some Qt6 default compiler flags.
SUBST_FILES.opt=	mkspecs/common/gcc-base.conf
SUBST_SED.opt=		-e 's,-O[s23],,'

SUBST_CLASSES.SunOS+=	vscript
SUBST_STAGE.vscript=	pre-configure
SUBST_FILES.vscript=	mkspecs/common/gcc-base-unix.conf
SUBST_SED.vscript=	-e '/QMAKE_LFLAGS_VERSION_SCRIPT/d'

SUBST_CLASSES+=		path
SUBST_STAGE.path=	pre-configure
SUBST_MESSAGE.path=	Add to default XDG path.
SUBST_FILES.path=	src/corelib/io/qstandardpaths_unix.cpp
SUBST_VARS.path=	PREFIX PKG_SYSCONFBASE

# The pri file has WRKSRC in it.
SUBST_CLASSES+=		pkgconf
SUBST_STAGE.pkgconf=	post-build
SUBST_MESSAGE.pkgconf=	Fixing pkg-config WRKSRC path.
SUBST_FILES.pkgconf=	mkspecs/qmodule.pri
SUBST_SED.pkgconf=	-e 's,PKG_CONFIG_EXECUTABLE = .*,PKG_CONFIG_EXECUTABLE = ${TOOLS_PATH.pkg-config},'

.if ${OPSYS} == "Linux"
QMAKE_EXTRA=		QMAKE_PLATFORM += linux
.else
QMAKE_EXTRA=
.endif

COMPILER=	gcc
.if !empty(PKGSRC_COMPILER:Mclang)
COMPILER+=	clang llvm
.endif

pre-configure:
	${SED}  -e 's:@PREFIX@:${PREFIX}:g' \
		-e 's:@X11BASE@:${X11BASE}:g' \
		-e 's:@COMPILER@:${COMPILER:Q}:g' \
		-e 's:@CC@:${CC:Q}:g' \
		-e 's:@CXX@:${CXX:Q}:g' \
		-e 's:@LDFLAGS@:${LDFLAGS:Q}:g' \
		-e 's:@CFLAGS@:${CFLAGS:Q}:g' \
		-e 's:@CXXFLAGS@:${CXXFLAGS:Q}:g' \
		-e 's:@NETWORK_LIBS@:${NETWORK_LIBS:Q}:g' \
		-e 's:@SYS_LIBS@:${SYS_LIBS:Q}:g' \
		-e 's:@LEX@:${LEX}:g' \
		-e 's:@YACC@:${TOOLS_CMDLINE_YACC:Q}:g' \
		-e 's:@AR@:${AR:Q}:g' \
		-e 's:@MKDIR@:${MKDIR}:g' \
		-e 's:@LIBQT@:${LIBQT:Q}:g' \
		-e 's:@PTHREAD_LDFLAGS@:${PTHREAD_LDFLAGS:Q}:g' \
		-e 's:@PTHREAD_LIBS@:${PTHREAD_LIBS:Q}:g' \
		-e 's:@COMPILER_RPATH_FLAG@:${COMPILER_RPATH_FLAG}:g' \
		-e 's:@QMAKE_RANLIB@:${RANLIB}:g' \
		-e 's:@QMAKE_EXTRA@:${QMAKE_EXTRA:Q}:g' \
		${FILESDIR}/${QMAKE_CONF} > ${WRKSRC}/qmake.conf
	for dir in ${WRKSRC}/mkspecs/*; do \
		${TEST} -d $${dir} || continue; \
		${RM} -f $${dir}/*.orig; \
		${TEST} -f $${dir}/qmake.conf || continue; \
		${CP} ${WRKSRC}/qmake.conf $${dir}; \
	done
	${RM} -f ${WRKSRC}/mkspecs/features/mac/default_pre.prf
	${RM} -f ${WRKSRC}/mkspecs/features/mac/default_post.prf

.if ${USE_CROSS_COMPILE:Uno:tl} == "yes" && ${OPSYS} == "NetBSD"
PLIST.targetmetadata=	yes
post-install: qt-target-metadata
.PHONY: qt-target-metadata
qt-target-metadata:
	${PERL5} ${FILESDIR}/target-metadata.pl ${DESTDIR:Q}${QTPREFIX:Q} \
	    ${CROSS_DESTDIR:Q} ${WRKDIR:Q} ${PREFIX:Q}

.endif

.include "options.mk"

.if ${OPSYS} == "Darwin" && ${USE_CROSS_COMPILE:Uno:tl} != "yes" && !empty(PKG_OPTIONS:Mhost-tools)
# CMake removes this build-tree rpath during installation.
BUILDLINK_PASSTHRU_RPATHDIRS+= ${WRKSRC}/lib
.endif

.if empty(PKG_OPTIONS:Mhost-tools)
.if ${USE_CROSS_COMPILE:Uno:tl} == "yes"
CMAKE_CONFIGURE_ARGS+=	-DOPENSSL_ROOT_DIR:PATH=${BUILDLINK_DIR}
.endif
CMAKE_CONFIGURE_ARGS+=	-DFEATURE_pkg_config:BOOL=ON
CMAKE_CONFIGURE_ARGS+=	-DFEATURE_publicsuffix_libpsl:BOOL=ON
CMAKE_CONFIGURE_ARGS+=	-DFEATURE_publicsuffix_qt:BOOL=OFF
CMAKE_CONFIGURE_ARGS+=	-DFEATURE_publicsuffix_system:BOOL=OFF
.endif
CMAKE_CONFIGURE_ARGS+=	-DQT_DISABLE_RPATH:BOOL=ON

.include "../../devel/cmake/configure-settings.mk"

CONFIGURE_ARGS+=	-- ${CMAKE_CONFIGURE_ARGS}
.if ${OPSYS} != "Darwin"
LDFLAGS+=		${COMPILER_RPATH_FLAG}${QTPREFIX}/lib
.else
CMAKE_INSTALL_NAME_DIR=	${QTPREFIX}/lib
.endif

TOOL_DEPENDS+=	xmlstarlet-[0-9]*:../../textproc/xmlstarlet

PKGCONFIG_OVERRIDE+=	lib/pkgconfig/Qt6Concurrent.pc
PKGCONFIG_OVERRIDE+=	lib/pkgconfig/Qt6Core.pc
PKGCONFIG_OVERRIDE+=	lib/pkgconfig/Qt6Gui.pc
PKGCONFIG_OVERRIDE+=	lib/pkgconfig/Qt6Network.pc
PKGCONFIG_OVERRIDE+=	lib/pkgconfig/Qt6OpenGL.pc
PKGCONFIG_OVERRIDE+=	lib/pkgconfig/Qt6OpenGLWidgets.pc
PKGCONFIG_OVERRIDE+=	lib/pkgconfig/Qt6PrintSupport.pc
PKGCONFIG_OVERRIDE+=	lib/pkgconfig/Qt6Sql.pc
PKGCONFIG_OVERRIDE+=	lib/pkgconfig/Qt6Test.pc
PKGCONFIG_OVERRIDE+=	lib/pkgconfig/Qt6Widgets.pc
PKGCONFIG_OVERRIDE+=	lib/pkgconfig/Qt6Xml.pc

# The host-tools option keeps only the dependencies of the Core host generators.
.include "../../archivers/zstd/buildlink3.mk"
.include "../../converters/libiconv/buildlink3.mk"
.include "../../devel/gettext-lib/buildlink3.mk"
.include "../../devel/pcre2/buildlink3.mk"
.include "../../devel/zlib/buildlink3.mk"
.include "../../lang/python/application.mk"
.include "../../math/double-conversion/buildlink3.mk"
.include "../../security/libb2/buildlink3.mk"
.if empty(PKG_OPTIONS:Mhost-tools)
.include "../../archivers/brotli/buildlink3.mk"
.include "../../databases/sqlite3/buildlink3.mk"
.include "../../devel/glib2/buildlink3.mk"
.if !empty(PLATFORM_SUPPORTS_WAYLAND:Myes)
PLIST.wayland=	yes
.include "../../devel/wayland/buildlink3.mk"
.endif
.include "../../fonts/harfbuzz/buildlink3.mk"
.include "../../graphics/freetype2/buildlink3.mk"
.include "../../graphics/png/buildlink3.mk"
.include "../../security/openssl/buildlink3.mk"
.include "../../textproc/icu/buildlink3.mk"
.include "../../textproc/md4c/buildlink3.mk"
.include "../../www/libproxy/buildlink3.mk"
BUILDLINK_API_DEPENDS.libpsl+= libpsl>=0.23.3nb2
.include "../../www/libpsl/buildlink3.mk"
.if ${OPSYS} != "Darwin"
PLIST.x11=	yes
.include "../../fonts/fontconfig/buildlink3.mk"
.include "../../graphics/glu/buildlink3.mk"
.include "../../graphics/vulkan-headers/buildlink3.mk"
.  if !empty(MESALIB_SUPPORTS_EGL:Myes)
PLIST.egl=	yes
.    if defined(EMBERBSD_COMMON_GRAPHICS)
# The modern Mesa dependency guarantees EGLDevice. Require the compiled
# feature too; early PLIST expansion must not depend on installed headers
# or a buildlink prefix cached by a later package phase.
PLIST.egldevice=	yes
CMAKE_CONFIGURE_ARGS+= -DFEATURE_eglfs_egldevice:BOOL=ON
.    else
EGL_EXT_HEADER= ${X11BASE}/include/EGL/eglext.h
.      if exists(${EGL_EXT_HEADER})
EGL_EXT_FILE=	cat ${EGL_EXT_HEADER:Q}
.        if !empty(EGL_EXT_FILE:sh:MEGL_DRM_MASTER_FD_EXT)
PLIST.egldevice=	yes
.        endif
.      endif
.    endif
.  endif
BUILDLINK_API_DEPENDS.libxcb+=	libxcb>=1.11
.include "../../x11/libxcb/buildlink3.mk"
.include "../../x11/xcb-util/buildlink3.mk"
.include "../../x11/xcb-util-cursor/buildlink3.mk"
.include "../../x11/xcb-util-image/buildlink3.mk"
.include "../../x11/xcb-util-keysyms/buildlink3.mk"
.include "../../x11/xcb-util-renderutil/buildlink3.mk"
.include "../../x11/xcb-util-wm/buildlink3.mk"
.include "../../x11/libSM/buildlink3.mk"
.include "../../x11/libX11/buildlink3.mk"
.include "../../x11/libXext/buildlink3.mk"
.include "../../x11/libXcursor/buildlink3.mk"
.include "../../x11/libXft/buildlink3.mk"
.include "../../x11/libXi/buildlink3.mk"
.include "../../x11/libXmu/buildlink3.mk"
.include "../../x11/libXrandr/buildlink3.mk"
.include "../../x11/libXrender/buildlink3.mk"
.include "../../x11/libxkbcommon/buildlink3.mk"
.endif
.include "../../mk/jpeg.buildlink3.mk"
.include "../../mk/krb5.buildlink3.mk"
.endif
.include "../../mk/pthread.buildlink3.mk"
.include "../../mk/atomic64.mk"
.include "../../mk/bsd.pkg.mk"

.if ${USE_CROSS_COMPILE:Uno:tl} == "yes" && ${OPSYS} == "NetBSD"
# Both recipes stage and normalize all files before selecting their package.
# PLIST and WRKDIR are defined by bsd.pkg.mk before these dependencies expand.
post-install: qtbase-select-stage
.PHONY: qtbase-select-stage
.PHONY: ${WRKDIR}/.qtbase-full-plist ${WRKDIR}/.qtbase-runtime-plist ${WRKDIR}/.qtbase-devel-plist
qtbase-select-stage: qt-target-metadata pkgconfig-link ${PLIST}
.for _qtbase_part in FULL RUNTIME DEVEL
	${MAKE} ${WRKDIR:Q}/.qtbase-${_qtbase_part:tl}-plist \
	    PLIST=${WRKDIR:Q}/.qtbase-${_qtbase_part:tl}-plist \
	    PLIST_SRC=${QTBASE_${_qtbase_part}_PLIST_SRC:Q}
.endfor
	${PERL5} ${FILESDIR}/select-package-stage.pl ${QTBASE_PACKAGE_PART:Q} \
	    ${DESTDIR:Q}${PREFIX:Q} ${WRKDIR:Q}/.qtbase-full-plist \
	    ${WRKDIR:Q}/.qtbase-runtime-plist ${WRKDIR:Q}/.qtbase-devel-plist ${PLIST:Q}
.endif
