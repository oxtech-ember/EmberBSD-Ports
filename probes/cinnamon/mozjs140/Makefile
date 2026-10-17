# SpiderMonkey JavaScript library (140.x branch, Firefox ESR 140 source).
# Cinnamon probe: cjs 140.1 requires the mozjs-140 pkg-config module.
# Derived from pkgsrc lang/mozjs128 (fff4deb63); NetBSD patches carried
# over where they are not i386-specific.
MOZVER=		140.17.0esr
DISTNAME=	firefox-${MOZVER}.source
PKGNAME=	mozjs140-${MOZVER:S/esr//}
CATEGORIES=	lang
MASTER_SITES=	${MASTER_SITE_MOZALL:=firefox/releases/${MOZVER}/source/}
EXTRACT_SUFX=	.tar.xz

MAINTAINER=	pkgsrc-users@NetBSD.org
HOMEPAGE=	https://spidermonkey.dev/
COMMENT=	SpiderMonkey JavaScript library (140.x branch)
LICENSE=	mpl-2.0

WRKSRC=		${WRKDIR}/firefox-${PKGVERSION_NOREV}
USE_TOOLS+=	gm4 gmake perl pkg-config
USE_LANGUAGES=	c c++

# "ERROR: Only GCC 8.1 or newer is supported"
GCC_REQD+=	8

# Firefox 140's standalone js/src configure no longer references
# cbindgen (the 128-line needed it); no host cbindgen is wired in.

# SpiderMonkey 140 dropped GNU-objdump support and requires llvm-objdump
# during configure and build. mozconfigure's check_prog honors the
# LLVM_OBJDUMP environment variable; Homebrew LLVM provides the tool.
CONFIGURE_ENV+=	LLVM_OBJDUMP=/opt/homebrew/opt/llvm/bin/llvm-objdump
MAKE_ENV+=	LLVM_OBJDUMP=/opt/homebrew/opt/llvm/bin/llvm-objdump
# Target objcopy from the cross binutils; the shared TOOLDIR owns it.
CONFIGURE_ENV+=	OBJCOPY=${TOOLDIR}/bin/aarch64--netbsd-objcopy
MAKE_ENV+=	OBJCOPY=${TOOLDIR}/bin/aarch64--netbsd-objcopy

CHECK_PORTABILITY_SKIP+=	security/nss/tests/libpkix/libpkix.sh
CHECK_PORTABILITY_SKIP+=	security/nss/tests/multinit/multinit.sh

CONFIGURE_DIRS=	js/src/build
BUILD_DIRS=	js/src/build

HAS_CONFIGURE=		yes
CONFIGURE_SCRIPT=	../configure
CONFIGURE_ARGS+=	--prefix=${PREFIX}
CONFIGURE_ARGS+=	--disable-debug
CONFIGURE_ARGS+=	--with-system-icu
CONFIGURE_ARGS+=	--with-system-zlib
CONFIGURE_ARGS+=	--enable-readline
CONFIGURE_ARGS+=	--disable-jemalloc
CONFIGURE_ARGS+=	--disable-debug-symbols
CONFIGURE_ARGS+=	--enable-strip
CONFIGURE_ARGS+=	--with-intl-api

OVERRIDE_GNU_CONFIG_SCRIPTS=	yes
OVERRIDE_DIRDEPTH=		4

# For rustc/cargo detection
.include "../../mk/bsd.prefs.mk"

.if ${MACHINE_PLATFORM:MSunOS-*}
CONFIGURE_ARGS+=	--target=x86_64-unknown-illumos
CONFIGURE_ARGS+=	--host=x86_64-unknown-illumos
.elif ${USE_CROSS_COMPILE:tl} == "yes"
# Mozilla cross semantics: --host is the machine running the build
# tools (rustc must run there), --target receives the NetBSD triple.
# The pkgsrc mozjs128 host==target form only fits native builds; with
# a Darwin build host it fails the rust host-triplet check.
CONFIGURE_ARGS+=	--host=${NATIVE_MACHINE_GNU_PLATFORM}
CONFIGURE_ARGS+=	--target=${MACHINE_GNU_PLATFORM}
# Host (build-machine) tools: Homebrew LLVM clang, because Apple clang
# rejects -fuse-ld= and mozconfigure's host-linker probe cannot
# identify Apple's classic ld. Homebrew clang pairs with its own lld.
# The host-linker probe needs a linker that self-identifies; route
# host links through the ld shim (lld banner, ld64.lld backend).
SHIMDIR=	/Volumes/BigData/EmberBSD/build/cinnamon-cross/host-ld-shim
CONFIGURE_ENV+=		HOST_CC=${SHIMDIR}/cc
CONFIGURE_ENV+=		HOST_CXX=${SHIMDIR}/cxx
# The TOOLBASE rustc sees the aarch64-unknown-netbsd std installed by
# lang/rust-std-aarch64-netbsd.
CONFIGURE_ENV+=		RUSTC=${TOOLBASE}/bin/rustc
CONFIGURE_ENV+=		CARGO=${TOOLBASE}/bin/cargo
# mozconfigure runs its own pkg-config discovery; point it at the
# pkgsrc wrapper so target sysroot modules (zlib, icu) resolve.
CONFIGURE_ENV+=		PKG_CONFIG=${TOOLS_CMD.pkg-config:Q}

# pkgsrc's builtin-zlib pc template ships with an empty Version field,
# which fails mozconfigure's "zlib >= 1.2.3" module constraint. Fill
# in the base-system zlib version before configure runs.
pre-configure:
	${RUN}${TEST} -f ${BUILDLINK_DIR}/lib/pkgconfig/zlib.pc || ${TRUE}
	${RUN}${SED} -e 's/^Version:$$/Version: 1.2.10/' \
		${BUILDLINK_DIR}/lib/pkgconfig/zlib.pc > ${BUILDLINK_DIR}/lib/pkgconfig/zlib.pc.tmp
	${RUN}${MV} ${BUILDLINK_DIR}/lib/pkgconfig/zlib.pc.tmp ${BUILDLINK_DIR}/lib/pkgconfig/zlib.pc
.else
CONFIGURE_ARGS+=	--target=${MACHINE_GNU_PLATFORM}
CONFIGURE_ARGS+=	--host=${MACHINE_GNU_PLATFORM}
.endif

# The mozjs128 readline -L@PREFIX@ subst is gone: Firefox 140's
# js/moz.configure no longer carries that check_symbol pattern, and the
# cross wrapper resolves the sysroot readline on its own.

PKGCONFIG_OVERRIDE+=	js/src/build/js.pc.in
PKGCONFIG_OVERRIDE+=	js/src/ctypes/libffi/libffi.pc.in

PYTHON_VERSIONS_INCOMPATIBLE=	27
PYTHON_FOR_BUILD_ONLY=		tool

post-install:
	cd ${DESTDIR}${PREFIX}/lib && \
		if [ -f libmozjs-140.so ] && [ ! -L libmozjs-140.so ]; then \
			${RM} -f libmozjs-140.so.0.0.0 libmozjs-140.so.0 && \
			${MV} libmozjs-140.so libmozjs-140.so.0.0.0; \
		fi && \
		${RM} -f libmozjs-140.so.0 libmozjs-140.so && \
		${LN} -s libmozjs-140.so.0.0.0 libmozjs-140.so.0 && \
		${LN} -s libmozjs-140.so.0 libmozjs-140.so
	${RM} -f ${DESTDIR}${PREFIX}/lib/libjs_static.ajs
	${CHMOD} -x ${DESTDIR}${PREFIX}/include/mozjs-140/js-config.h
	${CHMOD} -x ${DESTDIR}${PREFIX}/lib/pkgconfig/mozjs-140.pc

.include "../../converters/libiconv/buildlink3.mk"
.include "../../devel/zlib/buildlink3.mk"
# Compiled by the shared cross GCC16 toolchain only. The pkgsrc
# mozjs128 recipe carried a build-only clang dependency; SpiderMonkey
# documents GCC support (GCC_REQD above), so no second compiler
# enters this profile.
# Cross Rust for the SpiderMonkey icu4x crates: native host toolchain
# with the target std installed by lang/rust-std-aarch64-netbsd
# (librsvg cross.mk pattern; pkgsrc rust.mk has no Darwin-cross mode).
RUST_TYPE=	native
TOOL_DEPENDS+=	rust-bin-1.99.0{,nb[0-9]*}:../../lang/rust-bin
TOOL_DEPENDS+=	rust-std-aarch64-netbsd-1.99.0{,nb[0-9]*}:../../lang/rust-std-aarch64-netbsd
TOOLS_CREATE+=	cargo rustc
TOOLS_PATH.cargo=	${TOOLBASE}/bin/cargo
TOOLS_PATH.rustc=	${TOOLBASE}/bin/rustc
MAKE_ENV+=	RUSTC=${TOOLBASE}/bin/rustc
MAKE_ENV+=	CARGO_TARGET_AARCH64_UNKNOWN_NETBSD_LINKER=${WRAPPER_BINDIR}/cc
MAKE_ENV+=	CARGO_NET_OFFLINE=true
.include "../../lang/python/batteries-included.mk"
.include "../../lang/python/tool.mk"
.include "../../textproc/icu/buildlink3.mk"
.include "../../mk/readline.buildlink3.mk"
.include "../../mk/atomic64.mk"
.include "../../mk/bsd.pkg.mk"
