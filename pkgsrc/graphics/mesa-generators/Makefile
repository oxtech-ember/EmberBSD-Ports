# $NetBSD$
# Origin: Mesa 26.2.6 build-host shader generators.
.include "../MesaLib/mesa-source.mk"
PKGNAME= mesa-generators-${MESA_SOURCE_VERSION}
PKGREVISION= ${MESA_PORT_REVISION}
CATEGORIES= graphics
MAINTAINER= pkgsrc-users@NetBSD.org
HOMEPAGE= https://www.mesa3d.org/
COMMENT= Native Mesa shader generators for cross builds
LICENSE= mit

USE_LANGUAGES= c c++
USE_CXX_FEATURES= c++17
PYTHON_FOR_BUILD_ONLY= tool
PYTHON_VERSION_REQD= 315
MESON_REQD+= 1.12.1
USE_TOOLS+= bison flex pkg-config cmake
TOOL_DEPENDS+= bison-[0-9]*:../../devel/bison
TOOL_DEPENDS+= flex>=2.5.4a:../../devel/flex
.include "../../mk/bsd.prefs.mk"
TOOLS_PLATFORM.bison= ${TOOLBASE}/bin/bison
TOOLS_PLATFORM.flex= ${TOOLBASE}/bin/flex
TOOL_DEPENDS+= cmake>=4.4.4:../../devel/cmake
TOOL_DEPENDS+= pkgconf>=0:../../devel/pkgconf

TOOL_DEPENDS+= ${PYPKGPREFIX}-mako>=1.4.3:../../devel/py-mako
TOOL_DEPENDS+= ${PYPKGPREFIX}-packaging>=26.3:../../devel/py-packaging
TOOL_DEPENDS+= ${PYPKGPREFIX}-yaml>=6.0.3nb1:../../textproc/py-yaml
SUBST_CLASSES+= python
SUBST_STAGE.python= pre-configure
SUBST_FILES.python= meson.build
SUBST_SED.python= -e 's|@PYTHONBIN@|${TOOL_PYTHONBIN}|g'
BUILDLINK_API_DEPENDS.clang+= clang>=23.1.4<23.1.5
.include "../../lang/clang/buildlink3.mk"
BUILDLINK_API_DEPENDS.llvm+= llvm>=23.1.4<23.1.5
.include "../../lang/llvm/buildlink3.mk"
BUILDLINK_API_DEPENDS.spirv-headers+= spirv-headers>=1.4.363.0
BUILDLINK_DEPMETHOD.spirv-headers= build
.include "../../parallel/spirv-headers/buildlink3.mk"
BUILDLINK_API_DEPENDS.spirv-tools+= spirv-tools>=2026.4nb1
BUILDLINK_DEPMETHOD.spirv-tools= build
.include "../../parallel/spirv-tools/buildlink3.mk"
BUILDLINK_API_DEPENDS.spirv-llvm-translator+= spirv-llvm-translator>=23.1.2<23.2
.include "../../parallel/spirv-llvm-translator/buildlink3.mk"

MESON_ARGS+= -Dcpp_rtti=true
MESON_ARGS+= -Dauto_features=disabled -Dplatforms=[] -Dgallium-drivers=[] -Dvulkan-drivers=[]
MESON_ARGS+= -Dglx=disabled -Degl=disabled -Dgbm=disabled -Dopengl=false
MESON_ARGS+= -Dgles1=disabled -Dgles2=disabled -Dtools=imagination
MESON_ARGS+= -Dmesa-clc=enabled -Dinstall-mesa-clc=true
MESON_ARGS+= -Dmesa-clc-bundle-headers=enabled
MESON_ARGS+= -Dprecomp-compiler=enabled -Dinstall-precomp-compiler=true
MESON_ARGS+= -Dllvm=enabled -Dshared-llvm=enabled -Ddraw-use-llvm=false -Damd-use-llvm=false
MESON_ARGS+= -Dspirv-tools=enabled -Dbuild-tests=false -Db_ndebug=false
MESON_ARGS+= -Dallow-fallback-for=

.include "../../lang/python/tool.mk"
.include "../../devel/meson/build.mk"
.include "../../mk/bsd.pkg.mk"
