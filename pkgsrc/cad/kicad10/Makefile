# $NetBSD: Makefile,v 1.124 2026/09/02 19:01:04 wiz Exp $

V=		10.0.8
DISTNAME=	kicad-${V}
CATEGORIES=	cad
MASTER_SITES=	${MASTER_SITE_GITLAB:=kicad/code/}
GITLAB_PROJECT=	kicad
GITLAB_RELEASE=	${V}
EXTRACT_SUFX=	.tar.bz2

MAINTAINER=	pkgsrc-users@NetBSD.org
HOMEPAGE=	https://www.kicad.org/
COMMENT=	Schematic and PCB CAD software (stable branch)
LICENSE=	gnu-gpl-v3

TOOL_DEPENDS+=	swig4-[0-9]*:../../devel/swig4
TOOL_DEPENDS+=	lemon-[0-9]*:../../devel/lemon
DEPENDS+=	git-base-[0-9]*:../../devel/git-base
# Ship the default tables, matching libraries, templates, and 3D models.
DEPENDS+=	kicad-symbols-${V}{,nb*}:../../cad/kicad-symbols
DEPENDS+=	kicad-footprints-${V}{,nb*}:../../cad/kicad-footprints
DEPENDS+=	kicad-templates-${V}{,nb*}:../../cad/kicad-templates
DEPENDS+=	kicad-packages3d-${V}{,nb*}:../../cad/kicad-packages3d

USE_CXX_FEATURES=	charconv filesystem c++17
USE_PKGLOCALEDIR=	yes
USE_LANGUAGES=		c c++
USE_TOOLS+=		pkg-config msgfmt msgmerge xgettext

CMAKE_CONFIGURE_ARGS+=		-DCMAKE_BUILD_TYPE=Release
# Keep the default-on IPC API explicit; its providers are direct dependencies.
CMAKE_CONFIGURE_ARGS+=		-DKICAD_IPC_API=ON
CMAKE_CONFIGURE_ARGS+=		-DKICAD_SCRIPTING_WXPYTHON=OFF
CMAKE_CONFIGURE_ARGS+=		-DKICAD_BUILD_I18N=ON
CMAKE_CONFIGURE_ARGS+=		-DLEMON_EXE:FILEPATH=${TOOLBASE}/bin/lemon
CMAKE_CONFIGURE_ARGS+=		-DLEMON_TEMPLATE:FILEPATH=${TOOLBASE}/share/lemon/lempar.c

# KICAD_USE_EGL must be defined if wxWidgets was compiled with EGL canvas.
.include "../../graphics/MesaLib/features.mk"
.if !empty(MESALIB_SUPPORTS_EGL:Myes)
CMAKE_CONFIGURE_ARGS+=		-DKICAD_USE_EGL=ON
.else
CMAKE_CONFIGURE_ARGS+=		-DKICAD_USE_EGL=OFF
.endif

PY_PATCHPLIST=		yes
PYTHON_FOR_BUILD_ONLY=	no

PYTHON_VERSIONS_INCOMPATIBLE=	314 # Fails to find Python libs

# The package tries to build a native .app bundle. This doesn't work
# in pkgsrc context because they don't support DESTDIR installation,
# which is a requirement in pkgsrc. It also tries to use native Python
# frameworks, but has to use pkgsrc's. Getting this to build requires 15
# additional patches. Ping if you you want the patches.
# I didn't commit them yet because it segfaults. -tnn 20220102
NOT_FOR_PLATFORM+=	Darwin-*-*

.include "options.mk"

# KiCad requires ZSTD in CMakeLists.txt.
.include "../../archivers/gzip-hpp/buildlink3.mk"
.include "../../archivers/zstd/buildlink3.mk"
.include "../../cad/dxflib/buildlink3.mk"
.include "../../cad/occt/buildlink3.mk"
.include "../../databases/nanodbc/buildlink3.mk"
.include "../../databases/unixodbc/buildlink3.mk"
.include "../../devel/3dxware-sdk/buildlink3.mk"
.include "../../devel/argparse/buildlink3.mk"
.include "../../devel/boost-libs/buildlink3.mk"
.include "../../devel/compoundfilereader/buildlink3.mk"
.include "../../devel/dynamic_bitset/buildlink3.mk"
.include "../../devel/cmake/build.mk"
.include "../../devel/gettext-tools/msgfmt-desktop.mk"
.include "../../devel/libgit2/buildlink3.mk"
.include "../../devel/libcontext/buildlink3.mk"
.include "../../devel/libpopcnt/buildlink3.mk"
.include "../../devel/magic_enum/buildlink3.mk"
.if ${USE_CROSS_COMPILE:Uno:tl} == "yes"
BUILDLINK_API_DEPENDS.protobuf+=	protobuf>=36.2nb1
.else
BUILDLINK_API_DEPENDS.protobuf+=	protobuf>=36.2
.endif
.include "../../devel/protobuf/buildlink3.mk"
.include "../../devel/protobuf/host-protoc.mk"
.include "../../devel/py-pybind11/buildlink3.mk"
.include "../../devel/tl-expected/buildlink3.mk"
.include "../../devel/thread-pool/buildlink3.mk"
CMAKE_CONFIGURE_ARGS+=	-Dpybind11_DIR=${BUILDLINK_DIR}/${PYSITELIB}/pybind11/share/cmake/pybind11
CMAKE_CONFIGURE_ARGS+=	-DPYTHON_SITE_PACKAGE_PATH=${PYSITELIB}
.include "../../net/nng/buildlink3.mk"
.include "../../devel/zlib/buildlink3.mk"
.include "../../graphics/MesaLib/buildlink3.mk"
.include "../../graphics/cairo/buildlink3.mk"
.include "../../graphics/glad/buildlink3.mk"
BUILDLINK_API_DEPENDS.glm+=	glm>=0.9.9.8
.include "../../graphics/glm/buildlink3.mk"
.include "../../graphics/glu/buildlink3.mk"
.include "../../graphics/hicolor-icon-theme/buildlink3.mk"
.include "../../graphics/nanosvg/buildlink3.mk"
.include "../../graphics/potrace/buildlink3.mk"
.include "../../graphics/zint-lib/buildlink3.mk"
.include "../../lang/python/extension.mk"
.include "../../math/clipper2/buildlink3.mk"
.include "../../math/delaunator/buildlink3.mk"
.include "../../math/rectpack2d/buildlink3.mk"
.include "../../math/rtree/buildlink3.mk"
.include "../../math/fast_float/buildlink3.mk"
.include "../../math/nanoflann/buildlink3.mk"
.include "../../math/tinyspline/buildlink3.mk"
.include "../../print/poppler/buildlink3.mk"
.include "../../security/libsecret/buildlink3.mk"
.include "../../security/picosha2/buildlink3.mk"
.include "../../sysutils/desktop-file-utils/desktopdb.mk"
.include "../../textproc/PEGTL/buildlink3.mk"
.include "../../textproc/fmtlib/buildlink3.mk"
.include "../../textproc/json-schema-validator/buildlink3.mk"
.include "../../textproc/nlohmann-json/buildlink3.mk"
.include "../../textproc/rapidcsv/buildlink3.mk"
.include "../../textproc/sundown/buildlink3.mk"
.include "../../www/curl/buildlink3.mk"
.include "../../x11/libspnav/buildlink3.mk"
.include "../../x11/wxGTK32/buildlink3.mk"
# needs 64-bit CAS for std::atomic<size_t>
.include "../../mk/atomic64.mk"
.include "../../mk/bsd.pkg.mk"
