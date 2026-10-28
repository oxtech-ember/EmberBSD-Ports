# $NetBSD: Makefile,v 1.220 2026/04/06 10:47:10 wiz Exp $
# Origin: EmberBSD; AI-assisted bounded NetBSD 11/AArch64 and amd64 candidate.
DISTNAME=	mesa-26.2.5
PKGNAME=	${DISTNAME:S/mesa/MesaLib/}
PKGREVISION=	8
CATEGORIES=	graphics
MASTER_SITES=	https://archive.mesa3d.org/
EXTRACT_SUFX=	.tar.xz
MAINTAINER=	pkgsrc-users@NetBSD.org
HOMEPAGE=	https://www.mesa3d.org/
COMMENT=	OpenGL and Vulkan with RadeonSI, V3D, PowerVR, VirGL, Zink and software rendering
LICENSE=	mit
CONFLICTS+=	libglapi-[0-9]* libglvnd-[0-9]*
ONLY_FOR_PLATFORM=	NetBSD-11.*-aarch64 NetBSD-11.*-x86_64
USE_TOOLS+=	bison flex pkg-config xgettext
USE_LANGUAGES=	c c++
USE_CC_FEATURES+=	c11
USE_CXX_FEATURES+=	c++17
MESON_REQD+=	1.12.1
PYTHON_FOR_BUILD_ONLY=	tool
PYTHON_VERSION_REQD=	315
.include "../../mk/bsd.prefs.mk"
.include "../../lang/python/pyversion.mk"
.include "features.mk"
.include "options.mk"
.if ${USE_CROSS_COMPILE:Uno:tl} == "yes"
# Mesa lexers handle yywrap themselves. Flex only generates source on the host.
TOOL_DEPENDS+=	flex>=2.5.4a:../../devel/flex
TOOLS_PLATFORM.flex=	${TOOLBASE}/bin/flex
.endif
.if !defined(EMBERBSD_COMMON_GRAPHICS)
PKG_FAIL_REASON+= "Mesa requires the prepared common graphics profile"
.endif
.if ${DISTNAME} != "mesa-26.2.5" || ${PKGREVISION} != "8"
PKG_FAIL_REASON+= "The common graphics profile requires adapted MesaLib 26.2.5nb8"
.endif
TOOL_DEPENDS+=	${PYPKGPREFIX}-mako>=1.4.3:../../devel/py-mako
TOOL_DEPENDS+=	${PYPKGPREFIX}-packaging-[0-9]*:../../devel/py-packaging
TOOL_DEPENDS+=	${PYPKGPREFIX}-yaml>=6.0.3nb1:../../textproc/py-yaml
SUBST_CLASSES+=	python
SUBST_STAGE.python=	pre-configure
SUBST_FILES.python=	meson.build
SUBST_SED.python=	-e 's|@PYTHONBIN@|${TOOL_PYTHONBIN}|g'
# Zink loads the common Vulkan loader at runtime. An ICD stays optional.
DEPENDS+=	vulkan-loader>=1.4.357.0:../../graphics/vulkan-loader
PLIST_VARS+= intel v3d powervr radeonsi
.if ${MACHINE_ARCH} == "x86_64"
MESON_ARGS+=	-Dgallium-drivers=iris,radeonsi,virgl,softpipe,llvmpipe,zink
MESON_ARGS+=	-Dvulkan-drivers=
PLIST.intel=	yes
PLIST.radeonsi=	yes
_EMBERBSD_MESA_GENERATOR_PROFILES+= intel
_EMBERBSD_MESA_LLVM_TRIPLE=	x86_64-unknown-netbsd
BUILDLINK_API_DEPENDS.libdrm+=	libdrm>=2.4.134nb7
.else
MESON_ARGS+=	-Dgallium-drivers=v3d,virgl,softpipe,llvmpipe,zink
# One AArch64 package serves all boards. It contains the PowerVR and V3D ICDs.
MESON_ARGS+=	-Dvulkan-drivers=imagination,broadcom -Dimagination-srv=false
MESON_ARGS+=	-Dimagination-uscgen-devices= -Dvulkan-manifest-per-architecture=false
PLIST.v3d=	yes
PLIST.powervr=	yes
_EMBERBSD_MESA_GENERATOR_PROFILES+= powervr
_EMBERBSD_MESA_LLVM_TRIPLE=	aarch64-unknown-netbsd
.endif
MESON_ARGS+=	-Dplatforms=x11,wayland -Dglx=dri
MESON_ARGS+=	-Degl=enabled -Dgbm=enabled -Dglvnd=disabled
MESON_ARGS+=	-Dgles1=enabled -Dgles2=enabled -Dopengl=true
MESON_ARGS+=	-Dllvm=enabled -Dshared-llvm=enabled -Dllvm-orcjit=true
MESON_ARGS+=	-Dvulkan-layers= -Dtools=
.if !empty(_EMBERBSD_MESA_GENERATOR_PROFILES)
.if ${USE_CROSS_COMPILE:Uno:tl} == "yes"
# Cross builds run the matching sealed generators on the build host.
MESON_ARGS+= -Dmesa-clc=system -Dprecomp-compiler=system
MESON_ARGS+= -Dspirv-tools=disabled
_EMBERBSD_MESA_GENERATOR_NAMES= mesa_clc vtn_bindgen2
.if !empty(_EMBERBSD_MESA_GENERATOR_PROFILES:Mpowervr)
_EMBERBSD_MESA_GENERATOR_NAMES+= pco_clc
.endif
.include "mesa-generators.mk"
.else
# Native builds compile and run the upstream generators with the selected GCC.
# These libraries serve build-only tools. Mesa keeps its LLVM runtime link.
MESON_ARGS+= -Dmesa-clc=enabled -Dprecomp-compiler=enabled
MESON_ARGS+= -Dspirv-tools=enabled
MESON_ARGS+= -Dinstall-mesa-clc=false -Dinstall-precomp-compiler=false
BUILDLINK_DEPMETHOD.clang=	build
.include "../../lang/clang/buildlink3.mk"
BUILDLINK_DEPMETHOD.spirv-tools=	build
BUILDLINK_API_DEPENDS.spirv-tools+= spirv-tools>=2026.4nb1
.include "../../parallel/spirv-tools/buildlink3.mk"
# LLVM 23.1 requires Translator from the same major.minor release family.
BUILDLINK_API_DEPENDS.spirv-llvm-translator+= spirv-llvm-translator>=23.1.2<23.2
BUILDLINK_DEPMETHOD.spirv-llvm-translator=	build
.include "../../parallel/spirv-llvm-translator/buildlink3.mk"
.endif
.endif
MESON_ARGS+=	-Dgallium-va=disabled -Dgallium-mediafoundation=disabled
MESON_ARGS+=	-Dgallium-rusticl=false -Dteflon=false -Dperfetto=false
MESON_ARGS+=	-Dmicrosoft-clc=disabled -Dallow-fallback-for=
MESON_ARGS+=	-Dzlib=enabled -Dzstd=enabled -Ddisplay-info=disabled
MESON_ARGS+=	-Dlibunwind=disabled -Dvalgrind=disabled
# pkgsrc supplies --buildtype=plain and the selected compiler optimization.
MESON_ARGS+=	-Dbuild-tests=true -Db_lto=false
PKGCONFIG_OVERRIDE_STAGE=	pre-install
.for pc in gl glx egl gbm glesv1_cm glesv2 dri
PKGCONFIG_OVERRIDE+=	output/meson-private/${pc}.pc
.endfor
.include "../../lang/llvm/buildlink3.mk"
.if ${USE_CROSS_COMPILE:tl} == "yes"
USE_TOOLS+=	digest
# The accepted metadata tool records the real installed sysroot path.
_EMBERBSD_LLVM_SYSROOT!= cd ${CROSS_DESTDIR:Q} && pwd -P
BUILDLINK_TRANSFORM+= I:${_EMBERBSD_LLVM_SYSROOT}${PREFIX}:${BUILDLINK_DIR}
# This host executable must understand the target ELF format for ABI checks.
MESON_BINARIES+=	nm
MESON_BINARY.nm=	${TOOLDIR}/bin/${MACHINE_GNU_PLATFORM}-nm
.include "../../devel/wayland-protocols/cross-scanner.mk"
.endif
# The explicit absolute binary prevents Meson's default tool/CMake search.
MESON_BINARIES+=	llvm-config
MESON_BINARY.llvm-config=	${LLVM_CONFIG_PATH}
# Native and cross packages must pass the same staged ELF compatibility gate.
# The actual SDK API check runs in pre-configure before its first use.
_EMBERBSD_MESA_ELF_CHECK= ${TOOL_PYTHONBIN:Q} -B -E -S ${FILESDIR:Q}/check-dynamic-elf.py \
	--sdk-source ${EMBERBSD_SDK_SOURCE:U:Q} --arch ${MACHINE_ARCH:Q}
_EMBERBSD_MESA_STAGED_LIB= ${DESTDIR}${PREFIX}/lib
.if ${MACHINE_ARCH} == "x86_64"
# RadeonSI requires libelf. Qualify the OS base provider before Meson probes it.
.if ${USE_CROSS_COMPILE:Uno:tl} == "yes"
_EMBERBSD_MESA_LIBELF_MODE=	cross
_EMBERBSD_MESA_LIBELF_ROOT=	${CROSS_DESTDIR:U}
.if empty(CROSS_DESTDIR:M/*)
PKG_FAIL_REASON+= "Cross Mesa requires an absolute CROSS_DESTDIR for base libelf"
.endif
.else
_EMBERBSD_MESA_LIBELF_MODE=	native
_EMBERBSD_MESA_LIBELF_ROOT=	/
.endif
_EMBERBSD_MESA_LIBELF_RECIPE=	${.CURDIR:H:H}/devel/elftoolchain
_EMBERBSD_MESA_LIBELF_CHECK=	${TOOL_PYTHONBIN:Q} -B -E -S ${FILESDIR:Q}/check-base-libelf.py \
	--base-recipe ${_EMBERBSD_MESA_LIBELF_RECIPE:Q} \
	--sdk-source ${EMBERBSD_SDK_SOURCE:U:Q} \
	--target-root ${_EMBERBSD_MESA_LIBELF_ROOT:Q} \
	--buildlink-dir ${BUILDLINK_DIR:Q} \
	--mode ${_EMBERBSD_MESA_LIBELF_MODE:Q} --arch ${MACHINE_ARCH:Q}
.endif
pre-configure:
	${TEST} -x ${TOOL_PYTHONBIN:Q}
	${_EMBERBSD_MESA_ELF_CHECK} --check-sdk
	${TOOL_PYTHONBIN} -c 'import sys, mako, packaging, yaml; assert sys.version_info[:2] == tuple(map(int, "${PYVERSSUFFIX}".split(".")))'
.if ${MACHINE_ARCH} == "x86_64"
	${_EMBERBSD_MESA_LIBELF_CHECK}
.endif
.if ${USE_CROSS_COMPILE:tl} == "yes"
	${TEST} "$$(${TOOLS_CMD.pkg-config} --modversion wayland-client)" = 1.26.0
	${TEST} "$$(${LLVM_CONFIG_PATH} --host-target)" = ${_EMBERBSD_MESA_LLVM_TRIPLE:Q}
	${TEST} "$$(${LLVM_CONFIG_PATH} --prefix)" = ${_EMBERBSD_LLVM_SYSROOT:Q}/usr/pkg
	${TEST} "$$(${LLVM_CONFIG_PATH} --includedir)" = ${_EMBERBSD_LLVM_SYSROOT:Q}/usr/pkg/include
	${TEST} "$$(${LLVM_CONFIG_PATH} --libdir)" = ${_EMBERBSD_LLVM_SYSROOT:Q}/usr/pkg/lib
.endif
	${TEST} -x ${LLVM_CONFIG_PATH:Q}
	${TEST} "$$(${LLVM_CONFIG_PATH} --version)" = 23.1.4
	${TEST} "$$(${LLVM_CONFIG_PATH} --shared-mode --link-shared)" = shared
	${TEST} "$$(${LLVM_CONFIG_PATH} --has-rtti)" = YES
	${LLVM_CONFIG_PATH} --link-shared --libs core executionengine orcjit native > /dev/null
post-install:
	${_EMBERBSD_MESA_ELF_CHECK} --library-dir ${_EMBERBSD_MESA_STAGED_LIB:Q}

.include "../../x11/libdrm/buildlink3.mk"
.include "../../archivers/zstd/buildlink3.mk"
.include "../../devel/zlib/buildlink3.mk"
.include "../../textproc/expat/buildlink3.mk"
.include "../../devel/libudev-bsd/buildlink3.mk"
BUILDLINK_API_DEPENDS.wayland+= wayland>=1.26.0nb1
.include "../../devel/wayland/buildlink3.mk"
BUILDLINK_API_DEPENDS.wayland-protocols+= wayland-protocols>=1.49
.include "../../devel/wayland-protocols/buildlink3.mk"
BUILDLINK_API_DEPENDS.libX11+= libX11>=1.6
.include "../../x11/libX11/buildlink3.mk"
.include "../../x11/libXext/buildlink3.mk"
.include "../../x11/libXrandr/buildlink3.mk"
.include "../../x11/libXxf86vm/buildlink3.mk"
BUILDLINK_API_DEPENDS.libxcb+= libxcb>=1.13
.include "../../x11/libxcb/buildlink3.mk"
BUILDLINK_API_DEPENDS.libxshmfence+= libxshmfence>=1.1
.include "../../x11/libxshmfence/buildlink3.mk"
.include "../../x11/xorgproto/buildlink3.mk"
.include "../../x11/xcb-proto/buildlink3.mk"
.include "../../lang/python/tool.mk"
.include "../../devel/meson/build.mk"
.include "../../mk/pthread.buildlink3.mk"
.include "../../mk/atomic64.mk"
.include "../../mk/bsd.pkg.mk"

.if ${USE_CROSS_COMPILE:Uno:tl} == "yes" && ${_TOOLS_USE_PKGSRC.flex:Uyes:tl} != "no"
PKG_FAIL_REASON+= "Mesa cross builds require installed native Flex satisfying FLEX_REQD=${FLEX_REQD} at ${TOOLBASE}/bin/flex"
.endif
