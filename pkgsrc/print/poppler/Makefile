# $NetBSD: Makefile,v 1.132 2026/09/02 19:04:11 wiz Exp $

COMMENT=	PDF rendering library
PKGREVISION=	4

SUPERSEDES+=	poppler-glib-[0-9]*

.include "../../mk/bsd.prefs.mk"

TOOL_DEPENDS+=	glib2-introspection-[0-9]*:../../devel/glib2-introspection

PKGCONFIG_OVERRIDE+=	poppler.pc.cmake
PKGCONFIG_OVERRIDE+=	poppler-glib.pc.cmake

INSTALLATION_DIRS+=	include/poppler share/doc/poppler

# Don't compile GTK+ test program.
CMAKE_CONFIGURE_ARGS+=	-DBUILD_GTK_TESTS=OFF
# Build the GLib wrapper and its introspection metadata without GTK.
CMAKE_CONFIGURE_ARGS+=	-DENABLE_GLIB=ON
.if ${USE_CROSS_COMPILE:Uno:tl} == "yes"
# Native scanners use the shared executor for real target GType queries.
EMBERBSD_GI_MESON_OPTIONS= no
.include "../../devel/gobject-introspection/cross.mk"
# cwrappers map bare target includes into the sysroot. CMake can resolve
# symlinks, so remove both spellings from the generated scanner rule.
# Escape literal paths before using them as sed regular expressions.
_POPPLER_GI_ROOT_RE= ${CROSS_DESTDIR:C|[.[\\*^]|\\\\&|gW:S|,|\\,|gW}
_POPPLER_GI_REAL_ROOT_RE= ${CROSS_DESTDIR:tA:C|[.[\\*^]|\\\\&|gW:S|,|\\,|gW}
_POPPLER_GI_UNROOT= s,-I${_POPPLER_GI_ROOT_RE}/,-I/,g
_POPPLER_GI_UNROOT_REAL= s,-I${_POPPLER_GI_REAL_ROOT_RE}/,-I/,g
SUBST_CLASSES+=			girpaths
SUBST_STAGE.girpaths=		post-configure
SUBST_MESSAGE.girpaths=		Bare include paths for the introspection rule
SUBST_FILES.girpaths=		${CMAKE_BUILD_DIR}/glib/CMakeFiles/gir-typelibs.dir/build.make
SUBST_SED.girpaths=		-e ${_POPPLER_GI_UNROOT:Q} -e ${_POPPLER_GI_UNROOT_REAL:Q}

# Preserve pkgsrc's selected compiler wrappers and inspect ELF SONAMEs
# with the shared readelf wrapper, not the host dynamic loader.
_POPPLER_GI_CC= ${WRAPPER_BINDIR}/${CC:T}
_POPPLER_GI_CXX= ${WRAPPER_BINDIR}/${CXX:T}
post-patch: poppler-gi-shim
.PHONY: poppler-gi-shim
poppler-gi-shim:
	${MKDIR} ${WRKDIR:Q}/bin
	${PRINTF} '#!/bin/sh\nCC=%s\nCXX=%s\nexport CC CXX\nexport CWRAPPERS_CONFIG_DIR=%s\nexec %s --use-ldd-wrapper %s "$$@"\n' \
	    ${_POPPLER_GI_CC:Q:Q} ${_POPPLER_GI_CXX:Q:Q} ${CWRAPPERS_CONFIG_DIR:Q:Q} \
	    ${TOOLBASE:Q:Q}/bin/g-ir-scanner ${EMBERBSD_GI_FILESDIR:Q:Q}/elf-needed.sh > ${WRKDIR:Q}/bin/g-ir-scanner
	${CHMOD} +x ${WRKDIR:Q}/bin/g-ir-scanner
CMAKE_CONFIGURE_ARGS+=	-DINTROSPECTION_SCANNER=${WRKDIR}/bin/g-ir-scanner
CMAKE_CONFIGURE_ARGS+=	-DINTROSPECTION_COMPILER=${TOOLBASE}/bin/g-ir-compiler
.endif
# Don't build and install the tools
CMAKE_CONFIGURE_ARGS+=	-DENABLE_UTILS=OFF
# Don't compile poppler cpp wrapper.
CMAKE_CONFIGURE_ARGS+=	-DENABLE_CPP=OFF
# Don't compile poppler qt5/6 wrapper.
CMAKE_CONFIGURE_ARGS+=	-DENABLE_QT5=OFF
CMAKE_CONFIGURE_ARGS+=	-DENABLE_QT6=OFF
# Don't run gperf if it's present
CMAKE_CONFIGURE_ARGS+=	-DRUN_GPERF_IF_PRESENT=OFF

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
