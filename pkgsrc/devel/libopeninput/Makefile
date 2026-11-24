# $NetBSD: Makefile,v 1.2 2026/05/27 17:14:19 kikadf Exp $

.include "Makefile.common"

PKGREVISION=	12
COMMENT=	Wscons(4) and kqueue(2) based port of libinput
# The keyboard scan code mappings of systemd hwdb are LGPL-2.1-or-later.
LICENSE=	mit AND gnu-lgpl-v2.1

# Scan code mappings of PC keyboards; see patch-src_wskbdmap.c.
HWDB_SYSTEMD_VERSION=	262.2
HWDB_KEYBOARD=		systemd-${HWDB_SYSTEMD_VERSION}-60-keyboard.hwdb
DISTFILES=		${DEFAULT_DISTFILES} ${HWDB_KEYBOARD}
SITES.${HWDB_KEYBOARD}=	-https://raw.githubusercontent.com/systemd/systemd/v${HWDB_SYSTEMD_VERSION}/hwdb.d/60-keyboard.hwdb
EXTRACT_ONLY=		${DEFAULT_DISTFILES}

USE_TOOLS+=	pkg-config awk
UDEV_REQUIRED=	yes

# wscons
ONLY_FOR_PLATFORM=	NetBSD-*-*
ONLY_FOR_PLATFORM+=	OpenBSD-*-*

MESON_ARGS+=	--wrap-mode=nofallback
MESON_ARGS+=	-Ddebug-gui=false
MESON_ARGS+=	-Dlua-plugins=disabled
MESON_ARGS+=	-Dlibwacom=false
MESON_ARGS+=	-Ddocumentation=false
MESON_ARGS+=	-Dtests=false
# Upstream's default derives a build-host path from the target prefix.
# Its explicit search root must be the pkgsrc dependency view on both hosts.
MESON_ARGS+=	-Depoll-dir=${BUILDLINK_DIR}

PKGCONFIG_OVERRIDE+=		output/meson-private/libinput.pc
PKGCONFIG_OVERRIDE_STAGE=	post-build

INSTALLATION_DIRS+=	share/libinput/hwdb.d

post-extract:
	${CP} ${FILESDIR}/wskbd-hwdb.c ${FILESDIR}/wskbd-hwdb.h ${WRKSRC}/src/

post-patch:
	${AWK} -f ${FILESDIR}/keynames.awk \
	    ${WRKSRC}/include/linux/freebsd/input-event-codes.h \
	    > ${WRKSRC}/src/wskbd-keynames.h

post-install:
	${INSTALL_DATA} ${DISTDIR}/${HWDB_KEYBOARD} \
	    ${DESTDIR}${PREFIX}/share/libinput/hwdb.d/60-keyboard.hwdb
	${INSTALL_DATA} ${FILESDIR}/70-emberbsd-keyboard.hwdb \
	    ${DESTDIR}${PREFIX}/share/libinput/hwdb.d/70-emberbsd-keyboard.hwdb

.include "../../devel/meson/build.mk"
.include "../../devel/libepoll-shim/buildlink3.mk"
BUILDLINK_API_DEPENDS.input-headers+= input-headers>=1.31.3
.include "../../devel/input-headers/buildlink3.mk"
.include "../../mk/udev.buildlink3.mk"
.include "../../mk/bsd.pkg.mk"
