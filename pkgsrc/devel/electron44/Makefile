# Electron 45.2.1 runtime for NetBSD.
# Target execution, GUI and hardware acceptance remain pending.

DISTNAME=	electron-45.2.1
PKGREVISION=	1
CATEGORIES=	devel
# The source owner prepares the complete pinned workspace separately.  The
# controller verifies it; no prebuilt distribution ZIP is a build input.
DISTFILES=
# The selected workspace already contains the owner's complete patch series.
# Keep the pkgsrc scratch directory separate from that reusable source tree.
WRKSRC=		${WRKDIR}

CHROMIUM_VERSION=	156.0.8078.75

MAINTAINER=	oxtech-ember@users.noreply.github.com
HOMEPAGE=	https://www.electronjs.org/
COMMENT=	Build cross-platform desktop apps with JavaScript, HTML, and CSS
LICENSE=	mit AND mpl-2.0 AND modified-bsd

# Cross-build with the shared Clang/LLVM SDK and matching EmberBSD runtime.
# Select GCC only through an explicit platform profile.
USE_CROSS_COMPILE=	yes
USE_LANGUAGES=		c c++
USE_TOOLS+=		pkg-config

# The selected native flatc generates target headers during the build.
TOOL_DEPENDS+= flatbuffers>=25.12.19.1:../../devel/flatbuffers
TOOL_DEPENDS+= crc32c>=1.1.2:../../devel/crc32c
TOOL_DEPENDS+= libsrtp>=2.8.1:../../security/libsrtp
TOOL_DEPENDS+= libyuv>=0.0.1978:../../multimedia/libyuv

.if ${EMBERBSD_ELECTRON_SHARED_OPENH264:Uno} == "yes"
TOOL_DEPENDS+= openh264>=2.7.0:../../multimedia/openh264
.endif

.if ${EMBERBSD_ELECTRON_SHARED_CODECS:Uno} == "yes"
TOOL_DEPENDS+= dav1d>=1.5.4:../../multimedia/dav1d
TOOL_DEPENDS+= libaom>=3.15.2:../../multimedia/libaom
TOOL_DEPENDS+= libvpx>=1.17.0:../../multimedia/libvpx
TOOL_DEPENDS+= libopus>=1.6.1nb1:../../audio/libopus
TOOL_DEPENDS+= flac>=1.5.0nb1:../../audio/flac
.endif

.if ${EMBERBSD_ELECTRON_SHARED_FFMPEG:Uno} == "yes"
TOOL_DEPENDS+= ffmpeg9>=9.0.2nb7:../../multimedia/ffmpeg9
.endif

.if ${EMBERBSD_ELECTRON_SHARED_MINIZIP:Uno} == "yes"
TOOL_DEPENDS+= minizip-ng>=4.2.2nb2:../../archivers/minizip-ng
.endif

.if ${EMBERBSD_ELECTRON_SHARED_XML:Uno} == "yes"
TOOL_DEPENDS+= libxml2>=2.15.4nb5:../../textproc/libxml2
TOOL_DEPENDS+= libxslt>=1.1.45nb3:../../textproc/libxslt
.endif

.if ${EMBERBSD_ELECTRON_SHARED_IMAGE:Uno} == "yes"
TOOL_DEPENDS+= libjpeg-turbo>=3.2.1nb1:../../graphics/libjpeg-turbo
TOOL_DEPENDS+= libwebp>=1.6.0nb4:../../graphics/libwebp
.endif

.if ${EMBERBSD_ELECTRON_SHARED_FONT:Uno} == "yes"
TOOL_DEPENDS+= freetype2>=2.15.0nb2:../../graphics/freetype2
TOOL_DEPENDS+= harfbuzz>=15.0.0nb3:../../fonts/harfbuzz
.endif

# Shared native JavaScript providers selected by the Electron producer.
TOOL_DEPENDS+= node-electron-asar>=4.3.1:../../devel/node-electron-asar
TOOL_DEPENDS+= node-electron-docs-parser>=3.0.3:../../devel/node-electron-docs-parser
TOOL_DEPENDS+= node-electron-typescript-definitions>=10.0.0:../../devel/node-electron-typescript-definitions
TOOL_DEPENDS+= node-types-node>=26.6.6:../../devel/node-types-node
TOOL_DEPENDS+= node-pre-flight>=2.0.0:../../devel/node-pre-flight
TOOL_DEPENDS+= rolldown>=1.2.16:../../devel/rolldown
TOOL_DEPENDS+= node-semver>=7.8.5:../../devel/node-semver
TOOL_DEPENDS+= typescript>=7.0.2:../../lang/typescript
TOOL_DEPENDS+= node-primer-octicons>=19.42.0:../../devel/node-primer-octicons
TOOL_DEPENDS+= node-postcss-minify>=1.2.0:../../devel/node-postcss-minify
TOOL_DEPENDS+= rollup>=4.65.1:../../devel/rollup
TOOL_DEPENDS+= esbuild>=0.28.2:../../www/esbuild
TOOL_DEPENDS+= node-lit>=3.3.3:../../devel/node-lit
TOOL_DEPENDS+= node-types-dom-speech-recognition>=0.0.12:../../devel/node-types-dom-speech-recognition
TOOL_DEPENDS+= node-ts-proto>=2.18.3:../../devel/node-ts-proto
TOOL_DEPENDS+= node-acorn>=8.19.0:../../devel/node-acorn
TOOL_DEPENDS+= node-js-yaml>=5.5.0:../../devel/node-js-yaml
TOOL_DEPENDS+= node-yargs>=18.2.0:../../devel/node-yargs
TOOL_DEPENDS+= node-svgo>=4.1.0:../../devel/node-svgo
TOOL_DEPENDS+= node-uuid>=14.0.3:../../devel/node-uuid
TOOL_DEPENDS+= node-cssnano>=9.9.0:../../devel/node-cssnano
TOOL_DEPENDS+= node-postcss>=8.5.32:../../devel/node-postcss
TOOL_DEPENDS+= node-types-estree>=1.0.10:../../devel/node-types-estree
TOOL_DEPENDS+= node-types-filesystem>=0.0.36:../../devel/node-types-filesystem
TOOL_DEPENDS+= node-types-filewriter>=0.0.33:../../devel/node-types-filewriter
TOOL_DEPENDS+= node-types-json-schema>=7.0.15:../../devel/node-types-json-schema
TOOL_DEPENDS+= node-undici-types>=8.12.3:../../devel/node-undici-types

# Inputs and producer work are selected explicitly in producer.mk.
# The prepared source owner applies patches before the controller verifies it.
# Override the pkgsrc patch target so recipe-local patches are not applied twice.
do-patch:
	@${DO_NADA}

.include "../../mk/bsd.prefs.mk"
.include "producer.mk"

.include "runtime-dependencies.mk"
.include "../../mk/bsd.pkg.mk"
