# SPDX-License-Identifier: MIT
# Origin: EmberBSD (AI-assisted), based on the official ONNX Runtime release.
DISTNAME=	onnxruntime-1.31.0
CATEGORIES=	math
MASTER_SITES=	-https://codeload.github.com/microsoft/onnxruntime/tar.gz/refs/tags/v1.31.0
DISTFILES=	${DISTNAME}${EXTRACT_SUFX}
EXTRACT_ONLY=	${DISTNAME}${EXTRACT_SUFX}

DISTFILES+=	ort-abseil_cpp.zip
SITES.ort-abseil_cpp.zip=	-https://github.com/abseil/abseil-cpp/archive/refs/tags/20250814.0.zip
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
DISTFILES+=	ort-protobuf.tar.gz
SITES.ort-protobuf.tar.gz=	-https://github.com/protocolbuffers/protobuf/releases/download/v33.6/protobuf-33.6.tar.gz
DISTFILES+=	ort-re2.zip
SITES.ort-re2.zip=	-https://github.com/google/re2/archive/refs/tags/2024-07-02.zip
DISTFILES+=	ort-safeint.zip
SITES.ort-safeint.zip=	-https://github.com/dcleblanc/SafeInt/archive/refs/tags/3.0.28.zip
# This is a host generator archive. It is never installed in the target SDK.
DISTFILES+=	ort-protoc-linux-x64.zip
SITES.ort-protoc-linux-x64.zip=	-https://github.com/protocolbuffers/protobuf/releases/download/v33.6/protoc-33.6-linux-x86_64.zip

HOMEPAGE=	https://onnxruntime.ai/
COMMENT=	Shared standard ONNX CPU inference C and C++ API
LICENSE=	mit AND apache-2.0 AND modified-bsd AND boost-license AND mpl-2.0
PATCH_STRIP=	-p1

USE_LANGUAGES=		c c++
USE_CXX_FEATURES=	c++20
USE_TOOLS+=		gmake patch unzip
TOOL_DEPENDS+=		patch>=2.7.6:../../devel/patch
GCC_REQD+=		16.2
CMAKE_REQD+=		3.28
CONFIGURE_DIR=		cmake
BUILD_TARGET=		onnxruntime onnxruntime_providers_shared
PYTHON_FOR_BUILD_ONLY=	tool
PYTHON_VERSIONS_INCOMPATIBLE=	27 38 39
CMAKE_CONFIGURE_ARGS+=	-C ${.CURDIR}/features.cmake
CMAKE_CONFIGURE_ARGS+=	-DCMAKE_INSTALL_LIBDIR=lib
CMAKE_CONFIGURE_ARGS+=	-DCMAKE_INSTALL_RPATH=${PREFIX}/lib\;${PREFIX}/gcc16/lib
CMAKE_CONFIGURE_ARGS+=	-DPython_EXECUTABLE=${TOOL_PYTHONBIN}
CMAKE_CONFIGURE_ARGS+=	-DPatch_EXECUTABLE=${TOOLBASE}/bin/gpatch
CMAKE_CONFIGURE_ARGS+=	-Donnxruntime_CMAKE_DEPS_MIRROR_DIR=${WRKDIR}/dependencies

# The matching protoc runs on the build host. Native NetBSD builds it from
# the same pinned protobuf source; cross builds supply it explicitly.
.include "../../mk/bsd.prefs.mk"
.if !empty(USE_CROSS_COMPILE:M[yY][eE][sS])
.if !defined(ONNXRUNTIME_NATIVE_PROTOC)
PKG_FAIL_REASON+=	"Set ONNXRUNTIME_NATIVE_PROTOC to a native protobuf 33.6 protoc"
.else
CMAKE_CONFIGURE_ARGS+=	-DONNX_CUSTOM_PROTOC_EXECUTABLE=${ONNXRUNTIME_NATIVE_PROTOC}
.endif
.endif

post-extract:
	${SH} ${FILESDIR}/prepare-dependencies.sh ${DISTDIR} ${WRKDIR}/dependencies ${FILESDIR}/dependencies.tsv

# Install ORT's top-level rules. Its private static dependencies must not
# publish a second protobuf, Abseil or FlatBuffers development package.
do-install:
	cd ${WRKSRC}/${CONFIGURE_DIR}/${CMAKE_BUILD_DIR} && \
	    ${SETENV} ${INSTALL_ENV} cmake -DCMAKE_INSTALL_LOCAL_ONLY=ON -P cmake_install.cmake

post-install:
	${SH} ${FILESDIR}/install-licenses.sh ${WRKSRC} ${WRKSRC}/${CONFIGURE_DIR}/${CMAKE_BUILD_DIR} ${DESTDIR}${PREFIX} ${.CURDIR}

.include "../../devel/cmake/build.mk"
# All FetchContent URLs resolve to checksum-verified local distfiles.
# CMake must populate them rather than assume pre-existing _deps sources.
CMAKE_CONFIGURE_ARGS+=	-DFETCHCONTENT_FULLY_DISCONNECTED=OFF
.include "../../lang/python/tool.mk"
.include "../../local-robotics/eigen3/buildlink3.mk"
.include "../../mk/bsd.pkg.mk"
