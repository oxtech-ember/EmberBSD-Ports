# $NetBSD: Makefile,v 1.132 2026/09/02 19:04:11 wiz Exp $

COMMENT=	PDF rendering library
PKGREVISION=	3

SUPERSEDES+=	poppler-glib-[0-9]*

TOOL_DEPENDS+=	glib2-introspection-[0-9]*:../../devel/glib2-introspection

PKGCONFIG_OVERRIDE+=	poppler.pc.cmake
PKGCONFIG_OVERRIDE+=	poppler-glib.pc.cmake

INSTALLATION_DIRS+=	include/poppler share/doc/poppler

# Don't compile GTK+ test program.
CMAKE_CONFIGURE_ARGS+=	-DBUILD_GTK_TESTS=OFF
# Compile GLib wrapper which also needs gtk2
CMAKE_CONFIGURE_ARGS+=	-DENABLE_GLIB=ON
# Cross builds select the native introspection generators and resolve
# GType queries on the real target through the shared GI executor
# (devel/gobject-introspection/cross.mk), like the GStreamer packages.
EMBERBSD_GI_MESON_OPTIONS= no
.include "../../devel/gobject-introspection/cross.mk"
# The scanner shim injects the cross ldd wrapper; without it the scanner
# resolves target SONAMEs with the host ldd.
# The cross cwrapper strips -I flags with the absolute sysroot prefix, so
# the generated introspection rule must use bare target paths; the wrapper
# maps them into the sysroot itself.
SUBST_CLASSES+=			girpaths
SUBST_STAGE.girpaths=		post-configure
SUBST_MESSAGE.girpaths=		Bare include paths for the introspection rule
SUBST_FILES.girpaths=		cmake-pkgsrc-build/glib/CMakeFiles/gir-typelibs.dir/build.make
SUBST_SED.girpaths=		-e 's|-I/private/tmp/ember-common-stack/sysroot|-I|g'
SUBST_SED.girpaths+=		-e 's|-I/Volumes/BigData/EmberBSD/work/ember-common-stack/sysroot|-I|g'

post-patch: poppler-gi-shim
.PHONY: poppler-gi-shim
poppler-gi-shim:
	${MKDIR} ${WRKDIR}/bin
	${PRINTF} '#!/bin/sh\nCC=${WRKDIR}/.cwrapper/bin/aarch64--netbsd-gcc\nCXX=${WRKDIR}/.cwrapper/bin/aarch64--netbsd-g++\nexport CC CXX CWRAPPERS_CONFIG_DIR=${WRKDIR}/.cwrapper/config\nexec ${TOOLBASE}/bin/g-ir-scanner --use-ldd-wrapper ${EMBERBSD_GI_FILESDIR}/elf-needed.sh "$$@"\n' > ${WRKDIR}/bin/g-ir-scanner
	${CHMOD} +x ${WRKDIR}/bin/g-ir-scanner
CMAKE_CONFIGURE_ARGS+=	-DINTROSPECTION_SCANNER=${WRKDIR}/bin/g-ir-scanner
CMAKE_CONFIGURE_ARGS+=	-DINTROSPECTION_COMPILER=${TOOLBASE}/bin/g-ir-compiler
BUILDLINK_DEPMETHOD.gobject-introspection=	build
.include "../../devel/gobject-introspection/buildlink3.mk"
# Don't build and install the tools
CMAKE_CONFIGURE_ARGS+=	-DENABLE_UTILS=OFF
# Don't compile poppler cpp wrapper.
CMAKE_CONFIGURE_ARGS+=	-DENABLE_CPP=OFF
# Don't compile poppler qt5/6 wrapper.
CMAKE_CONFIGURE_ARGS+=	-DENABLE_QT5=OFF
CMAKE_CONFIGURE_ARGS+=	-DENABLE_QT6=OFF
# Don't run gperf if it's present
CMAKE_CONFIGURE_ARGS+=	-DRUN_GPERF_IF_PRESENT=OFF

.include "../../mk/bsd.prefs.mk"

.if ${OPSYS} == "Darwin"
# MacOS Xcode does not provide /usr/include, so be explicit
CMAKE_CONFIGURE_ARGS+=	-DGLIB2_INCLUDE_DIRS=${PREFIX}/include
.endif

.if ${USE_CROSS_COMPILE:tl} == "yes"
ALL_ENV+=		PKG_CONFIG_SYSROOT_DIR=${CROSS_DESTDIR:Q}
CMAKE_CONFIGURE_ARGS+=	-DCMAKE_SYSROOT:STRING=${CROSS_DESTDIR:Q}
.endif

# Passing "-ansi" turns "long long" support off on FreeBSD/amd64:
.if ${OPSYS} == "FreeBSD" && ${MACHINE_ARCH} == "x86_64"
CFLAGS+=	-D__LONG_LONG_SUPPORTED=
.endif

.include "../../print/poppler/Makefile.common"

post-install:
	${INSTALL_MAN} ${WRKSRC}/README.md ${DESTDIR}${PREFIX}/share/doc/poppler/
	${INSTALL_MAN} ${WRKSRC}/README-XPDF ${DESTDIR}${PREFIX}/share/doc/poppler/
	${RMDIR} ${DESTDIR}${PREFIX}/include/poppler || ${TRUE}

.include "../../devel/boost-libs/buildlink3.mk"
BUILDLINK_API_DEPENDS.fontconfig+=	fontconfig>=2.15
.include "../../fonts/fontconfig/buildlink3.mk"
BUILDLINK_API_DEPENDS.glib2+=   glib2>=2.80.0
.include "../../devel/glib2/buildlink3.mk"
BUILDLINK_DEPMETHOD.gobject-introspection=      build
.include "../../devel/gobject-introspection/buildlink3.mk"
BUILDLINK_API_DEPENDS.cairo+=   cairo>=1.18
.include "../../graphics/cairo/buildlink3.mk"
.include "../../graphics/lcms2/buildlink3.mk"
.include "../../graphics/png/buildlink3.mk"
.include "../../graphics/tiff/buildlink3.mk"
.include "../../lang/python/tool.mk"
.include "../../www/curl/buildlink3.mk"
.include "../../mk/jpeg.buildlink3.mk"
.include "../../mk/pthread.buildlink3.mk"
.include "../../mk/bsd.pkg.mk"
