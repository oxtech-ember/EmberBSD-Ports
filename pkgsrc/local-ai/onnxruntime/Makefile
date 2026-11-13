# SPDX-License-Identifier: MIT
# Origin: EmberBSD (AI-assisted), based on the official ONNX Runtime release.
DISTNAME=	onnxruntime-1.31.0
PKGREVISION=	4
CATEGORIES=	math
MASTER_SITES=	-https://codeload.github.com/microsoft/onnxruntime/tar.gz/refs/tags/v1.31.0
DISTFILES=	${DISTNAME}${EXTRACT_SUFX}
EXTRACT_ONLY=	${DISTNAME}${EXTRACT_SUFX}

DISTFILES+=	ort-date.zip
SITES.ort-date.zip=	-https://github.com/HowardHinnant/date/archive/refs/tags/v3.0.1.zip
DISTFILES+=	ort-flatbuffers.zip
SITES.ort-flatbuffers.zip=	-https://github.com/google/flatbuffers/archive/refs/tags/v23.5.26.zip
DISTFILES+=	ort-json.zip
SITES.ort-json.zip=	-https://github.com/nlohmann/json/archive/refs/tags/v3.11.3.zip
DISTFILES+=	ort-microsoft_gsl.zip
SITES.ort-microsoft_gsl.zip=	-https://github.com/microsoft/GSL/archive/refs/tags/v4.2.1.zip
DISTFILES+=	ort-mp11.zip
SITES.ort-mp11.zip=	-https://github.com/boostorg/mp11/archive/refs/tags/boost-1.82.0.zip
DISTFILES+=	ort-onnx.zip
SITES.ort-onnx.zip=	-https://github.com/onnx/onnx/archive/refs/tags/v1.22.0.zip
DISTFILES+=	ort-re2.zip
SITES.ort-re2.zip=	-https://github.com/google/re2/archive/refs/tags/2024-07-02.zip
DISTFILES+=	ort-safeint.zip
SITES.ort-safeint.zip=	-https://github.com/dcleblanc/SafeInt/archive/refs/tags/3.0.28.zip

HOMEPAGE=	https://onnxruntime.ai/
COMMENT=	Shared ONNX Runtime C/C++ API with optional WebGPU plugin
LICENSE=	mit AND apache-2.0 AND modified-bsd AND boost-license AND mpl-2.0
PATCH_STRIP=	-p1

USE_LANGUAGES=		c c++
USE_CXX_FEATURES=	c++20
USE_TOOLS+=		gmake patch unzip
CHECK_PORTABILITY_SKIP+=	onnxruntime/test/python/transformers/benchmark_mha.sh
TOOL_DEPENDS+=		patch>=2.7.6:../../devel/patch
GCC_REQD+=		16.2
CMAKE_REQD+=		3.28
CONFIGURE_DIR=		cmake
BUILD_TARGET=		onnxruntime onnxruntime_providers_shared
PLIST_VARS+=		webgpu
PYTHON_FOR_BUILD_ONLY=	tool
PYTHON_VERSIONS_INCOMPATIBLE=	27 38 39
CMAKE_CONFIGURE_ARGS+=	-C ${.CURDIR}/features.cmake
CMAKE_CONFIGURE_ARGS+=	-DCMAKE_INSTALL_LIBDIR=lib
CMAKE_CONFIGURE_ARGS+=	-DCMAKE_INSTALL_RPATH=${PREFIX}/lib\;${PREFIX}/gcc16/lib
CMAKE_CONFIGURE_ARGS+=	-DPython_EXECUTABLE=${TOOL_PYTHONBIN}
CMAKE_CONFIGURE_ARGS+=	-DPatch_EXECUTABLE=${TOOLBASE}/bin/gpatch
CMAKE_CONFIGURE_ARGS+=	-Donnxruntime_CMAKE_DEPS_MIRROR_DIR=${WRKDIR}/dependencies

.include "../../mk/bsd.prefs.mk"
.include "../../devel/protobuf/host-protoc.mk"
CMAKE_CONFIGURE_ARGS+=	-DONNX_CUSTOM_PROTOC_EXECUTABLE=${PROTOC_FOR_BUILD:Q}
.include "options.mk"
.if !empty(PKG_OPTIONS:Mwebgpu)
# Reproducibly assembled from the ORT-pinned Dawn and its DEPS inputs.
DISTFILES+=	ort-dawn-v20260916.214021-sources.tar.gz
EXTRACT_ONLY+=	ort-dawn-v20260916.214021-sources.tar.gz
# The source bundle uses POSIX PAX paths longer than the ustar name field.
EXTRACT_USING=	bsdtar
SITES.ort-dawn-v20260916.214021-sources.tar.gz=	-https://github.com/oxtech-ember/EmberBSD-Ports/releases/download/onnxruntime-dawn-v20260916.214021/ort-dawn-v20260916.214021-sources.tar.gz
.endif

post-extract:
	${SH} ${FILESDIR}/prepare-dependencies.sh ${DISTDIR} ${WRKDIR}/dependencies ${FILESDIR}/dependencies.tsv
	${MKDIR} ${WRKSRC}/onnxruntime/core/platform/netbsd
	${CP} ${FILESDIR}/netbsd-device_discovery.cc \
	    ${WRKSRC}/onnxruntime/core/platform/netbsd/device_discovery.cc
.if !empty(PKG_OPTIONS:Mwebgpu)
	${TEST} -f ${WRKDIR}/dawn-20260916.214021/CMakeLists.txt || \
	    ${FAIL_MSG} "Dawn sources missing after extract"
	${SH} ${FILESDIR}/patch-dawn-netbsd-platform.sh ${WRKDIR}/dawn-20260916.214021
.endif

pre-configure:
.if !empty(PKG_OPTIONS:Mwebgpu)
	${TEST} -f ${WRKDIR}/dawn-20260916.214021/CMakeLists.txt || \
	    ${FAIL_MSG} "Dawn sources missing before configure"
.endif

# Install only ORT's top-level rules; shared dependencies belong to Ports.
# Upstream only installs the WebGPU plugin target when BUILD_SHARED_LIB is
# OFF; with the shared plugin EP we copy the module ourselves.
do-install:
	cd ${WRKSRC}/${CONFIGURE_DIR}/${CMAKE_BUILD_DIR} && \
	    ${SETENV} ${INSTALL_ENV} cmake -DCMAKE_INSTALL_LOCAL_ONLY=ON -P cmake_install.cmake
.if !empty(PKG_OPTIONS:Mwebgpu)
	${INSTALL_LIB} \
	    ${WRKSRC}/${CONFIGURE_DIR}/${CMAKE_BUILD_DIR}/libonnxruntime_providers_webgpu.so \
	    ${DESTDIR}${PREFIX}/lib/
.endif

post-install:
	${SH} ${FILESDIR}/install-licenses.sh ${WRKSRC} ${WRKSRC}/${CONFIGURE_DIR}/${CMAKE_BUILD_DIR} ${DESTDIR}${PREFIX} ${.CURDIR}
.if !empty(PKG_OPTIONS:Mwebgpu)
	${INSTALL_DATA_DIR} ${DESTDIR}${PREFIX}/share/licenses/onnxruntime/dawn
	${INSTALL_DATA} ${WRKDIR}/dawn-20260916.214021/LICENSE ${DESTDIR}${PREFIX}/share/licenses/onnxruntime/dawn/LICENSE
	${INSTALL_DATA} ${WRKDIR}/dawn-20260916.214021/third_party/webgpu-headers/LICENSE ${DESTDIR}${PREFIX}/share/licenses/onnxruntime/dawn/webgpu-headers-LICENSE
	${INSTALL_DATA} ${BUILDLINK_DIR}/share/licenses/spirv-headers/LICENSE ${DESTDIR}${PREFIX}/share/licenses/onnxruntime/dawn/spirv-headers-LICENSE
	${INSTALL_DATA} ${WRKDIR}/dawn-20260916.214021/third_party/renderdoc/LICENSE.md ${DESTDIR}${PREFIX}/share/licenses/onnxruntime/dawn/renderdoc-LICENSE.md
	${INSTALL_DATA} ${WRKDIR}/dawn-20260916.214021/third_party/vulkan-headers/src/LICENSE.md ${DESTDIR}${PREFIX}/share/licenses/onnxruntime/dawn/vulkan-headers-LICENSE.md
	${INSTALL_DATA} ${WRKDIR}/dawn-20260916.214021/third_party/vulkan-utility-libraries/src/LICENSE.md ${DESTDIR}${PREFIX}/share/licenses/onnxruntime/dawn/vulkan-utility-LICENSE.md
.endif

# Clang/libc++ on NetBSD needs locale_t / *_l before <locale>.
.include "../../mk/bsd.prefs.mk"
.if !empty(PKGSRC_COMPILER:Mclang)
CXXFLAGS+=	-D_NETBSD_SOURCE -include locale.h -Wno-error=deprecated-attributes
.endif

.include "../../devel/cmake/build.mk"
# All FetchContent URLs resolve to checksum-verified local distfiles.
# CMake must populate them rather than assume pre-existing _deps sources.
CMAKE_CONFIGURE_ARGS+=	-DFETCHCONTENT_FULLY_DISCONNECTED=OFF
.include "../../lang/python/tool.mk"
.include "../../devel/abseil/buildlink3.mk"
.include "../../devel/protobuf/buildlink3.mk"
.include "../../math/eigen3/buildlink3.mk"
.include "../../mk/bsd.pkg.mk"
