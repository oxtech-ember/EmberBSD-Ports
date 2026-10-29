.include "../../mk/bsd.prefs.mk"
.if ${USE_CROSS_COMPILE:Uno:tl} == "yes" && ${OPSYS} == "NetBSD" && !empty(EMBER_LLVM_CXX_STAGE:U)
EMBER_LLVM_CXX_COMPONENT= libcxx
.include "../../lang/compiler-rt/runtime-package.mk"
.else
# Origin: EmberBSD contributors (AI-assisted).
# The runtime source and complete patch set belong to lang/compiler-rt.
.include "../../lang/llvm/version.mk"

PKGREVISION=	1
PKGNAME=	libcxx-${LLVM_VERSION}
CATEGORIES=	lang devel
MAINTAINER=	pkgsrc-users@NetBSD.org
HOMEPAGE=	https://libcxx.llvm.org/
COMMENT=	LLVM C++ standard library for the selected host ABI
LICENSE=	apache-2.0

DISTINFO_FILE=	${.CURDIR}/../../lang/llvm/distinfo
NO_EXTRACT=	yes
NO_PATCH=	yes
NO_CONFIGURE=	yes
USE_LANGUAGES=	# producer selects the native compiler
USE_TOOLS+=	find sort tar
PYTHON_FOR_BUILD_ONLY=	tool
TOOL_DEPENDS+=	cmake>=4.0:../../devel/cmake
TOOL_DEPENDS+=	ninja-build>=1.13.2:../../devel/ninja-build
TOOL_DEPENDS+=	patch>=2.8.1:../../devel/patch
BUILD_DEFS+=	EMBERBSD_SDK_SOURCE OSX_SDK_PATH MACOSX_DEPLOYMENT_TARGET

.include "../../mk/bsd.prefs.mk"
.if ${OPSYS} != "Darwin" || ${USE_CROSS_COMPILE:Uno:tl} == "yes"
PKG_FAIL_REASON+= "This package currently supports the selected native Darwin ABI; target runtimes use the compiler-rt producer"
.endif

GENERATE_PLIST= cd ${DESTDIR:Q}${PREFIX:Q} && ${FIND} include/libc++ lib/libc++ share/libc++ share/doc/libcxx \( -type f -o -type l \) -print | ${SORT};
INSTALLATION_DIRS= . share/doc/libcxx

do-build:
	${PYTHONBIN:Q} ${.CURDIR:Q}/../../lang/compiler-rt/files/runtime.py --sdk-source ${EMBERBSD_SDK_SOURCE:Q} \
	    --pkgsrc-root ${PKGSRCDIR:Q} prepare --archive ${DISTDIR:Q}/${DISTNAME:Q}${EXTRACT_SUFX:Q} \
	    --patch ${TOOLBASE:Q}/bin/gpatch --source ${WRKDIR:Q}/runtime-source
	${PYTHONBIN:Q} ${.CURDIR:Q}/../../lang/compiler-rt/files/native.py --sdk-source ${EMBERBSD_SDK_SOURCE:Q} \
	    --pkgsrc-root ${PKGSRCDIR:Q} --source ${WRKDIR:Q}/runtime-source --host-prefix ${PREFIX:Q} \
	    --macos-sdk ${OSX_SDK_PATH:Q} --macos-minimum ${MACOSX_DEPLOYMENT_TARGET:Q} \
	    --work ${WRKDIR:Q}/runtime-build --stage ${WRKDIR:Q}/runtime-stage --jobs ${MAKE_JOBS:U1}

do-install:
	${TAR} -cf ${WRKDIR:Q}/libcxx-stage.tar -C ${WRKDIR:Q}/runtime-stage${PREFIX:Q} .
	${TAR} -xf ${WRKDIR:Q}/libcxx-stage.tar -C ${DESTDIR:Q}${PREFIX:Q}
	${INSTALL_DATA} ${WRKDIR:Q}/runtime-source/libcxx/LICENSE.TXT ${DESTDIR:Q}${PREFIX:Q}/share/doc/libcxx/LICENSE.TXT

.include "../../lang/python/tool.mk"
.include "../../mk/bsd.pkg.mk"

.endif
