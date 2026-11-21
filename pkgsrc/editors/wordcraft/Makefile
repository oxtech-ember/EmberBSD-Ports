# $NetBSD$
# Origin: ArtCraft Team and contributors; EmberBSD packaging (AI-assisted).

DISTNAME=	wordcraft-0.18.1
CATEGORIES=	editors
MASTER_SITES=	${MASTER_SITE_GITHUB:=storytold/}
GITHUB_TAG=	v${PKGVERSION_NOREV}
MAINTAINER=	pkgsrc-users@NetBSD.org
HOMEPAGE=	https://github.com/storytold/wordcraft
COMMENT=	Desktop word processor with native DOCX editing and a command line
LICENSE=	(mit OR apache-2.0) AND ofl-v1.1 AND cc0-1.0-universal AND modified-bsd

RUST_REQ=	1.95
EMBER_CARGO_PATCH_SET=	yes
EMBER_CARGO_PATCH_CRATES=	wgpu-30.0.1 wgpu-core-30.0.1 x11rb-0.13.2
USE_LANGUAGES=	c c++
USE_TOOLS+=	pkg-config
DISTFILES=	${DEFAULT_DISTFILES}

# The upstream workspace pins individual Git crates and translation catalogs.
CRAFT_I18N_REV=	1e515422afdda2f317af430c1f9d68a5f83935b4
.for project revision in \
	craft-libs 01315d9c92b5b0e69082d35ca56099461a1efd45 \
	craft-libs 6e03f65bf45181db77ba6229716e6624db9eb25b \
	craft-libs 762a06a4c6b48b522b7d4de84a87917ef90265e6 \
	craft-libs 92d392cff132eaf53e13afff77f38b5c11b73aa0 \
	craft-libs a3e0b5a9440d18f19422a9dca13516747b7d3181 \
	craft-libs fd5e2feff6ea25bed371a99cc732b3968d621505 \
	egui 6d518fc799681571963842f95b55a6b68431b15a \
	winit a517b3846ee8457d84ee4975110bfda6797c44dc \
	winprint.rs 417ac3c4d14d3da5485a99c7d5ce8f05664ec312 \
	winprint.rs 5f80b9baf6b58937c401656634e42d33f00ddf49 \
	craft-i18n ${CRAFT_I18N_REV}
DISTFILES+=	${project}-${revision}.tar.gz
SITES.${project}-${revision}.tar.gz= -https://codeload.github.com/storytold/${project}/tar.gz/${revision}
.endfor

MAKE_ENV+=	CRAFT_I18N_DIR=${WRKDIR}/craft-i18n-${CRAFT_I18N_REV}
MAKE_ENV+=	CRAFT_I18N_REQUIRED=1
CARGO_ARGS=	--config ${WRKDIR}/wordcraft-git.toml build --release --locked ${DEFAULT_CARGO_ARGS} -p wordcraft -p wordcraft-cli

.include "../../mk/bsd.prefs.mk"

APP_ID=		ai.storyteller.wordcraft
INSTALLATION_DIRS+= bin share/applications share/metainfo share/mime/packages
INSTALLATION_DIRS+= share/licenses/wordcraft
ICON_SIZES=	16 24 32 48 64 128 256 512
.for size in ${ICON_SIZES}
INSTALLATION_DIRS+= share/icons/hicolor/${size}x${size}/apps
.endfor
INSTALLATION_DIRS+= share/icons/hicolor/scalable/apps

pre-configure:
	${TOOL_PYTHONBIN} -B -I -S ${FILESDIR}/wordcraft-cargo-git.py \
	    --lockfile ${WRKSRC}/Cargo.lock --work ${WRKDIR} --config ${WRKDIR}/wordcraft-git.toml

do-install:
	${RUN} target=${EMBER_CARGO_TARGET:Q}; \
		test -n "$$target" || target=$$(${EMBER_CARGO_PREFIX}/bin/rustc --print host-tuple); \
		${INSTALL_PROGRAM} ${EMBER_CARGO_OUTPUT}/$$target/release/wordcraft \
		    ${EMBER_CARGO_OUTPUT}/$$target/release/wordcraft-cli ${DESTDIR}${PREFIX}/bin
	${INSTALL_DATA} ${WRKSRC}/packaging/linux/${APP_ID}.desktop ${DESTDIR}${PREFIX}/share/applications
	${INSTALL_DATA} ${WRKSRC}/packaging/linux/${APP_ID}.mime.xml ${DESTDIR}${PREFIX}/share/mime/packages/${APP_ID}.xml
	${SED} -e 's/@VERSION@/${PKGVERSION_NOREV}/g' -e 's/@DATE@/2026-11-12/g' \
	    ${WRKSRC}/packaging/linux/${APP_ID}.metainfo.xml.in > ${DESTDIR}${PREFIX}/share/metainfo/${APP_ID}.metainfo.xml
.for size in ${ICON_SIZES}
	${INSTALL_DATA} ${WRKSRC}/assets/app-icon/hicolor/${size}x${size}/apps/${APP_ID}.png \
	    ${DESTDIR}${PREFIX}/share/icons/hicolor/${size}x${size}/apps
.endfor
	${INSTALL_DATA} ${WRKSRC}/assets/app-icon/hicolor/scalable/apps/${APP_ID}.svg \
	    ${DESTDIR}${PREFIX}/share/icons/hicolor/scalable/apps
	${INSTALL_DATA} ${WRKSRC}/LICENSE-APACHE ${WRKSRC}/LICENSE-MIT ${WRKSRC}/ATTRIBUTION.md \
	    ${WRKSRC}/NOTICE ${WRKSRC}/assets/fonts/OFL-*.txt ${DESTDIR}${PREFIX}/share/licenses/wordcraft

.include "cargo-depends.mk"
.include "../../lang/rust/emberbsd-cargo.mk"
.if ${OPSYS} == "NetBSD"
# Winit and wgpu load their display, input and rendering libraries at runtime.
DEPENDS+=	MesaLib-[0-9]*:../../graphics/MesaLib
DEPENDS+=	libX11-[0-9]*:../../x11/libX11
DEPENDS+=	libxcb-[0-9]*:../../x11/libxcb
DEPENDS+=	libXcursor-[0-9]*:../../x11/libXcursor
DEPENDS+=	libXi-[0-9]*:../../x11/libXi
DEPENDS+=	libxkbcommon-[0-9]*:../../x11/libxkbcommon
.include "../../devel/wayland/buildlink3.mk"
.endif
.include "../../graphics/hicolor-icon-theme/buildlink3.mk"
.include "../../databases/shared-mime-info/mimedb.mk"
.include "../../sysutils/desktop-file-utils/desktopdb.mk"
.include "../../mk/bsd.pkg.mk"
