# $NetBSD: Makefile,v 1.220 2026/04/06 10:47:10 wiz Exp $
# Origin: EmberBSD; AI-assisted bounded NetBSD 11/AArch64 and amd64 candidate.
DISTNAME=	mesa-26.2.4
PKGNAME=	${DISTNAME:S/mesa/MesaLib/}
PKGREVISION=	7
CATEGORIES=	graphics
MASTER_SITES=	https://archive.mesa3d.org/
EXTRACT_SUFX=	.tar.xz
MAINTAINER=	pkgsrc-users@NetBSD.org
HOMEPAGE=	https://www.mesa3d.org/
COMMENT=	Open source OpenGL with V3D, VirGL, Zink and software rendering
LICENSE=	mit
CONFLICTS+=	libglapi-[0-9]* libglvnd-[0-9]*
ONLY_FOR_PLATFORM=	NetBSD-11.*-aarch64 NetBSD-11.*-x86_64
USE_TOOLS+=	bison flex pkg-config xgettext
USE_LANGUAGES=	c c++
USE_CC_FEATURES+=	c11
USE_CXX_FEATURES+=	c++17
GCC_REQD+=	16.2
MESON_REQD+=	1.12.1
PYTHON_FOR_BUILD_ONLY=	tool
PYTHON_VERSION_REQD=	315
.include "../../mk/bsd.prefs.mk"
.include "../../lang/python/pyversion.mk"
.include "features.mk"
.include "options.mk"
.if !defined(EMBERBSD_COMMON_GRAPHICS)
PKG_FAIL_REASON+= "Mesa requires the prepared common graphics profile"
.endif
.if ${DISTNAME} != "mesa-26.2.4" || ${PKGREVISION} != "7"
PKG_FAIL_REASON+= "The common graphics profile requires adapted MesaLib 26.2.4nb7"
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
PLIST_VARS+= intel v3d
.if ${MACHINE_ARCH} == "x86_64"
MESON_ARGS+=	-Dgallium-drivers=iris,virgl,softpipe,llvmpipe,zink
PLIST.intel=	yes
_EMBERBSD_MESA_GENERATOR_PROFILES+= intel
_EMBERBSD_MESA_LLVM_TRIPLE=	x86_64-unknown-netbsd
BUILDLINK_API_DEPENDS.libdrm+=	libdrm>=2.4.134nb3
.else
MESON_ARGS+=	-Dgallium-drivers=v3d,virgl,softpipe,llvmpipe,zink
PLIST.v3d=	yes
_EMBERBSD_MESA_LLVM_TRIPLE=	aarch64-unknown-netbsd
.endif
MESON_ARGS+=	-Dplatforms=x11,wayland -Dglx=dri
MESON_ARGS+=	-Degl=enabled -Dgbm=enabled -Dglvnd=disabled
MESON_ARGS+=	-Dgles1=enabled -Dgles2=enabled -Dopengl=true
MESON_ARGS+=	-Dllvm=enabled -Dshared-llvm=enabled -Dllvm-orcjit=true
MESON_ARGS+=	-Dvulkan-layers= -Dtools=
.if !empty(PKG_OPTIONS:Mpowervr)
MESON_ARGS+=	-Dvulkan-drivers=imagination -Dimagination-srv=false
_EMBERBSD_MESA_GENERATOR_PROFILES+= powervr
MESON_ARGS+=	-Dimagination-uscgen-devices= -Dvulkan-manifest-per-architecture=false
.else
MESON_ARGS+=	-Dvulkan-drivers=
.endif
.if !empty(_EMBERBSD_MESA_GENERATOR_PROFILES)
# Iris and PowerVR compile shaders on the build host with the same sealed tools.
MESON_ARGS+= -Dmesa-clc=system -Dprecomp-compiler=system
_EMBERBSD_MESA_GENERATOR_NAMES= mesa_clc vtn_bindgen2
.if !empty(_EMBERBSD_MESA_GENERATOR_PROFILES:Mpowervr)
_EMBERBSD_MESA_GENERATOR_NAMES+= pco_clc
.endif
.include "mesa-generators.mk"
.endif
MESON_ARGS+=	-Dgallium-va=disabled -Dgallium-mediafoundation=disabled
MESON_ARGS+=	-Dgallium-rusticl=false -Dteflon=false -Dperfetto=false
MESON_ARGS+=	-Dspirv-tools=disabled -Dmicrosoft-clc=disabled -Dallow-fallback-for=
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
pre-configure:
	${TEST} -x ${TOOL_PYTHONBIN:Q}
	${TOOL_PYTHONBIN} -c 'import sys, mako, packaging, yaml; assert sys.version_info[:2] == (3, 14)'
.if ${USE_CROSS_COMPILE:tl} == "yes"
	${TEST} "$$(${TOOLS_CMD.pkg-config} --modversion wayland-client)" = 1.26.0
	${TEST} -s ${LLVM_CONFIG_PATH:H:H:Q}/inputs.sha256
	${TEST} -f ${LLVM_CONFIG_PATH:H:H:Q}/receipt.json
	cd ${LLVM_CONFIG_PATH:H:H:Q} && \
	while read -r expected file; do \
		${TEST} "$${#expected}" -eq 64 || exit 1; \
		actual=$$(${TOOLS_DIGEST} SHA256 "$$file") || exit 1; \
		${TEST} "$${actual##* }" = "$$expected" || { \
			echo "LLVM helper receipt mismatch: $$file" >&2; exit 1; \
		}; \
	done < inputs.sha256
	${TEST} "$$(${LLVM_CONFIG_PATH} --host-target)" = ${_EMBERBSD_MESA_LLVM_TRIPLE:Q}
	${TEST} "$$(${LLVM_CONFIG_PATH} --prefix)" = ${_EMBERBSD_LLVM_SYSROOT:Q}/usr/pkg
	${TEST} "$$(${LLVM_CONFIG_PATH} --includedir)" = ${_EMBERBSD_LLVM_SYSROOT:Q}/usr/pkg/include
	${TEST} "$$(${LLVM_CONFIG_PATH} --libdir)" = ${_EMBERBSD_LLVM_SYSROOT:Q}/usr/pkg/lib
.endif
	${TEST} -x ${LLVM_CONFIG_PATH:Q}
	${TEST} "$$(${LLVM_CONFIG_PATH} --version)" = 23.1.3
	${TEST} "$$(${LLVM_CONFIG_PATH} --shared-mode --link-shared)" = shared
	${TEST} "$$(${LLVM_CONFIG_PATH} --has-rtti)" = YES
	${LLVM_CONFIG_PATH} --link-shared --libs core executionengine orcjit native > /dev/null
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
