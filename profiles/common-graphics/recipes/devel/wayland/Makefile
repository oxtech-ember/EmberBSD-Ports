# $NetBSD: Makefile,v 1.35 2026/03/26 08:53:11 wiz Exp $
# Origin: EmberBSD (AI-assisted), current Wayland with a matching host scanner.

EMBERBSD_WAYLAND_PKGDIR:= ${.PARSEDIR:tA}
WAYLAND_VERSION=	1.26.0
DISTNAME=	wayland-${WAYLAND_VERSION}
PKGREVISION=	1
CATEGORIES=	devel
MASTER_SITES=	https://gitlab.freedesktop.org/wayland/wayland/-/releases/${PKGVERSION_NOREV}/downloads/
EXTRACT_SUFX=	.tar.xz

MAINTAINER=	pkgsrc-users@NetBSD.org
HOMEPAGE=	https://wayland.freedesktop.org/
COMMENT=	Display server protocol - development libraries
LICENSE=	mit

# Documentation is disabled; the scanner validates DTDs through libxml2.

USE_TOOLS+=	pkg-config

USE_LANGUAGES=	c c++

MESON_ARGS+=	-Ddocumentation=false
MESON_ARGS+=	-Dtests=true

CFLAGS.NetBSD+=	-D_NETBSD_SOURCE

PKGCONFIG_OVERRIDE_STAGE=	pre-install
PKGCONFIG_OVERRIDE+=		output/meson-private/wayland-client.pc
PKGCONFIG_OVERRIDE+=		output/meson-private/wayland-cursor.pc
PKGCONFIG_OVERRIDE+=		output/meson-private/wayland-egl-backend.pc
PKGCONFIG_OVERRIDE+=		output/meson-private/wayland-egl.pc
PKGCONFIG_OVERRIDE+=		output/meson-private/wayland-scanner.pc
PKGCONFIG_OVERRIDE+=		output/meson-private/wayland-server.pc

.include "../../mk/bsd.prefs.mk"

.if defined(EMBERBSD_WAYLAND_DEVEL)
.if ${EMBERBSD_WAYLAND_DEVEL} != "yes" || ${PKGPATH} != "devel/wayland-devel"
PKG_FAIL_REASON+= "The wayland SDK role belongs to devel/wayland-devel"
.endif
PKGNAME=	wayland-devel-${WAYLAND_VERSION}
COMMENT=	Wayland target SDK for the development-host sysroot
DISTINFO_FILE=	${EMBERBSD_WAYLAND_PKGDIR}/distinfo
PATCHDIR=	${EMBERBSD_WAYLAND_PKGDIR}/patches
FILESDIR=	${EMBERBSD_WAYLAND_PKGDIR}/files
.if ${USE_CROSS_COMPILE:Uno:tl} != "yes" || ${OPSYS} != "NetBSD"
PKG_FAIL_REASON+= "The separate wayland SDK requires a NetBSD cross build; native wayland keeps its full package"
.endif
.endif

PLIST_VARS+=	runtime_split
.if ${USE_CROSS_COMPILE:Uno:tl} == "yes" && ${OPSYS} == "NetBSD"
.if ${MACHINE_ARCH} != "aarch64" && ${MACHINE_ARCH} != "x86_64"
PKG_FAIL_REASON+= "The wayland runtime/SDK split requires the common aarch64 or amd64 cross target"
.endif
PKGREVISION=	2
.if ${PKGREVISION} != 2
PKG_FAIL_REASON+= "The wayland runtime/SDK split requires package revision 2"
.endif
PLIST.runtime_split=	yes
WAYLAND_FULL_PLIST_SRC=	${EMBERBSD_WAYLAND_PKGDIR}/PLIST
WAYLAND_RUNTIME_PLIST_SRC=	${EMBERBSD_WAYLAND_PKGDIR}/PLIST.runtime
WAYLAND_DEVEL_PLIST_SRC=	${EMBERBSD_WAYLAND_PKGDIR}/../wayland-devel/PLIST
.if defined(EMBERBSD_WAYLAND_DEVEL)
WAYLAND_PACKAGE_PART=	devel
.if ${WAYLAND_PACKAGE_PART} != "devel"
PKG_FAIL_REASON+= "The wayland SDK recipe must select the devel partition"
.endif
PLIST_SRC=	${WAYLAND_DEVEL_PLIST_SRC}
DEPENDS+=	wayland-${WAYLAND_VERSION}nb2:../../devel/wayland
CONFLICTS+=	wayland<${WAYLAND_VERSION}nb2
.else
WAYLAND_PACKAGE_PART=	runtime
.if ${WAYLAND_PACKAGE_PART} != "runtime"
PKG_FAIL_REASON+= "The wayland runtime recipe must select the runtime partition"
.endif
PLIST_SRC=	${WAYLAND_RUNTIME_PLIST_SRC}
.endif
USE_TOOLS+=	perl:build
.endif

.if ${OPSYS} == "NetBSD" && ${OPSYS_VERSION} < 100000
CFLAGS.NetBSD+=	-Dppoll=pollts
.endif

.if ${USE_CROSS_COMPILE:tl} == "yes"
# wayland runs wayland-scanner at build-time.
.if defined(EMBERBSD_WAYLAND_SCANNER)
.include "cross-scanner.mk"
MESON_ARGS+=	-Dcross_scanner=${EMBERBSD_WAYLAND_SCANNER:Q}
.else
TOOL_DEPENDS+=	wayland-${WAYLAND_VERSION}{,nb[0-9]*}:../../devel/wayland
MESON_ARGS+=	-Dcross_scanner=${TOOLBASE:Q}/bin/wayland-scanner
.endif
.endif

.include "platform.mk"
.include "../../devel/meson/build.mk"
.if ${OPSYS} != "Linux"
.  include "../../devel/libepoll-shim/buildlink3.mk"
CPPFLAGS+=	-I${BUILDLINK_PREFIX.libepoll-shim}/include/libepoll-shim
.endif
.include "../../devel/libffi/buildlink3.mk"
.include "../../textproc/expat/buildlink3.mk"
.include "../../textproc/libxml2/buildlink3.mk"
.include "../../mk/bsd.pkg.mk"

.if ${USE_CROSS_COMPILE:Uno:tl} == "yes" && ${OPSYS} == "NetBSD"
# Each ordinary recipe stages the complete, unchanged upstream installation.
post-install: wayland-select-stage
.PHONY: wayland-select-stage
.PHONY: ${WRKDIR}/.wayland-full-plist ${WRKDIR}/.wayland-runtime-plist ${WRKDIR}/.wayland-devel-plist
wayland-select-stage: ${PLIST}
	${RUN} ember_wayland_dest=${DESTDIR:Q}; \
	    test -n "$$ember_wayland_dest" && test "$$ember_wayland_dest" != /
	${INSTALL_DATA_DIR} ${DESTDIR}${PREFIX}/share/licenses/wayland
	${INSTALL_DATA} ${WRKSRC}/COPYING ${DESTDIR}${PREFIX}/share/licenses/wayland/COPYING
.for _wayland_part in FULL RUNTIME DEVEL
	${MAKE} ${WRKDIR:Q}/.wayland-${_wayland_part:tl}-plist \
	    PLIST=${WRKDIR:Q}/.wayland-${_wayland_part:tl}-plist \
	    PLIST_SRC=${WAYLAND_${_wayland_part}_PLIST_SRC:Q}
.endfor
	${PERL5} ${FILESDIR}/select-package-stage.pl ${WAYLAND_PACKAGE_PART:Q} \
	    ${DESTDIR:Q}${PREFIX:Q} ${WRKDIR:Q}/.wayland-full-plist \
	    ${WRKDIR:Q}/.wayland-runtime-plist ${WRKDIR:Q}/.wayland-devel-plist ${PLIST:Q}
.endif
