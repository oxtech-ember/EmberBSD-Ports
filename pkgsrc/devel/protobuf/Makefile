# $NetBSD: Makefile,v 1.112 2026/09/01 09:04:13 adam Exp $
#
# When updating this, please also update devel/py-protobuf.
#
# NB: This package has very strange library versioning, lacking the
# usual libfoo.so.X symlink to libfoo.so.X.Y.  Thus, any change to the
# so version, e.g. .25.2.0 to .25.3.0, is an ABI change.  It is highly
# likely that any upstream release, even if apparently minor, will
# require a recursive revbump.

# Origin: EmberBSD (AI-assisted); current common provider with reviewed fixes.
EMBERBSD_PROTOBUF_PKGDIR:= ${.PARSEDIR:tA}
PROTOBUF_VERSION=	36.2
DISTNAME=	protobuf-${PROTOBUF_VERSION}
CATEGORIES=	devel
MASTER_SITES=	${MASTER_SITE_GITHUB:=protocolbuffers/}
GITHUB_PROJECT=	protobuf
GITHUB_RELEASE=	v${PKGVERSION_NOREV}

MAINTAINER=	pkgsrc-users@NetBSD.org
HOMEPAGE=	https://github.com/protocolbuffers/protobuf
COMMENT=	Google protocol buffers
LICENSE=	modified-bsd

USE_LANGUAGES=		c c++
USE_CXX_FEATURES=	c++17
FORCE_CXX_STD=		c++17

CMAKE_CONFIGURE_ARGS+=	-Dprotobuf_LOCAL_DEPENDENCIES_ONLY=ON
CMAKE_CONFIGURE_ARGS+=	-Dprotobuf_BUILD_SHARED_LIBS=ON
# requires googletest to be checked out in third_party/googletest
CMAKE_CONFIGURE_ARGS+=	-Dprotobuf_BUILD_TESTS=OFF

# illumos ld.so lazy PLT binding can invoke .init_array mid-init, re-entering
# a __cxa_guard-protected singleton and deadlocking.  protobuf generates these
# in .pb.cc files, so force BIND_NOW to resolve all PLT entries before init.
LDFLAGS.SunOS+=		-Wl,-z,now

# the [[ command will skip a test that would otherwise run
CHECK_PORTABILITY_SKIP+=	src/google/protobuf/compiler/zip_output_unittest.sh

.include "../../mk/bsd.prefs.mk"

.if defined(EMBERBSD_PROTOBUF_DEVEL)
.if ${EMBERBSD_PROTOBUF_DEVEL} != "yes" || ${PKGPATH} != "devel/protobuf-devel"
PKG_FAIL_REASON+= "The protobuf SDK role belongs to devel/protobuf-devel"
.endif
PKGNAME=	protobuf-devel-${PROTOBUF_VERSION}
COMMENT=	Protocol buffers target SDK for the development-host sysroot
DISTINFO_FILE=	${EMBERBSD_PROTOBUF_PKGDIR}/distinfo
PATCHDIR=	${EMBERBSD_PROTOBUF_PKGDIR}/patches
FILESDIR=	${EMBERBSD_PROTOBUF_PKGDIR}/files
.if ${USE_CROSS_COMPILE:Uno:tl} != "yes" || ${OPSYS} != "NetBSD"
PKG_FAIL_REASON+= "The separate protobuf SDK requires a NetBSD cross build; native protobuf keeps its full package"
.endif
.endif

PLIST_VARS+=	runtime_split
.if ${USE_CROSS_COMPILE:Uno:tl} == "yes" && ${OPSYS} == "NetBSD"
.if ${MACHINE_ARCH} != "aarch64" && ${MACHINE_ARCH} != "x86_64"
PKG_FAIL_REASON+= "The protobuf runtime/SDK split requires the common aarch64 or amd64 cross target"
.endif
PKGREVISION=	1
.if ${PKGREVISION} != 1
PKG_FAIL_REASON+= "The protobuf runtime/SDK split requires package revision 1"
.endif
PLIST.runtime_split=	yes
PROTOBUF_FULL_PLIST_SRC=	${EMBERBSD_PROTOBUF_PKGDIR}/PLIST
PROTOBUF_RUNTIME_PLIST_SRC=	${EMBERBSD_PROTOBUF_PKGDIR}/PLIST.runtime
PROTOBUF_DEVEL_PLIST_SRC=	${EMBERBSD_PROTOBUF_PKGDIR}/../protobuf-devel/PLIST
.if defined(EMBERBSD_PROTOBUF_DEVEL)
PROTOBUF_PACKAGE_PART=	devel
.if ${PROTOBUF_PACKAGE_PART} != "devel"
PKG_FAIL_REASON+= "The protobuf SDK recipe must select the devel partition"
.endif
PLIST_SRC=	${PROTOBUF_DEVEL_PLIST_SRC}
DEPENDS+=	protobuf-${PROTOBUF_VERSION}nb1:../../devel/protobuf
CONFLICTS+=	protobuf<${PROTOBUF_VERSION}nb1
.else
PROTOBUF_PACKAGE_PART=	runtime
.if ${PROTOBUF_PACKAGE_PART} != "runtime"
PKG_FAIL_REASON+= "The protobuf runtime recipe must select the runtime partition"
.endif
PLIST_SRC=	${PROTOBUF_RUNTIME_PLIST_SRC}
.endif
USE_TOOLS+=	perl:build
.endif

.include "../../devel/cmake/build.mk"
#.include "../../devel/googletest/buildlink3.mk"
BUILDLINK_API_DEPENDS.abseil+=	abseil>=20260817.0nb2
.include "../../devel/abseil/buildlink3.mk"
BUILDLINK_API_DEPENDS.zlib+=	zlib>=1.3.2
.include "../../devel/zlib/buildlink3.mk"
.include "../../mk/pthread.buildlink3.mk"
.include "../../mk/atomic64.mk"
.include "../../mk/bsd.pkg.mk"

.if ${USE_CROSS_COMPILE:Uno:tl} == "yes" && ${OPSYS} == "NetBSD"
# Each ordinary recipe stages the complete, unchanged upstream installation.
post-install: protobuf-select-stage
.PHONY: protobuf-select-stage
.PHONY: ${WRKDIR}/.protobuf-full-plist ${WRKDIR}/.protobuf-runtime-plist ${WRKDIR}/.protobuf-devel-plist
protobuf-select-stage: ${PLIST}
	${RUN} ember_protobuf_dest=${DESTDIR:Q}; \
	    test -n "$$ember_protobuf_dest" && test "$$ember_protobuf_dest" != /
	${INSTALL_DATA_DIR} ${DESTDIR}${PREFIX}/share/licenses/protobuf
	${INSTALL_DATA} ${WRKSRC}/LICENSE ${DESTDIR}${PREFIX}/share/licenses/protobuf/LICENSE
	${INSTALL_DATA} ${WRKSRC}/third_party/utf8_range/LICENSE ${DESTDIR}${PREFIX}/share/licenses/protobuf/utf8_range-LICENSE
.for _protobuf_part in FULL RUNTIME DEVEL
	${MAKE} ${WRKDIR:Q}/.protobuf-${_protobuf_part:tl}-plist \
	    PLIST=${WRKDIR:Q}/.protobuf-${_protobuf_part:tl}-plist \
	    PLIST_SRC=${PROTOBUF_${_protobuf_part}_PLIST_SRC:Q}
.endfor
	${PERL5} ${FILESDIR}/select-package-stage.pl ${PROTOBUF_PACKAGE_PART:Q} \
	    ${DESTDIR:Q}${PREFIX:Q} ${WRKDIR:Q}/.protobuf-full-plist \
	    ${WRKDIR:Q}/.protobuf-runtime-plist ${WRKDIR:Q}/.protobuf-devel-plist ${PLIST:Q}
.endif
