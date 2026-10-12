# $NetBSD: version.mk,v 1.22 2026/09/02 20:22:38 adam Exp $
# used by devel/lld
# used by devel/lldb
# used by devel/polly
# used by lang/clang
# used by lang/clang-tools-extra
# used by lang/compiler-rt
# used by lang/flang
# used by lang/libclc
# used by lang/libcxx
# used by lang/libcxxabi
# used by lang/libunwind
# used by lang/mlir
# used by lang/wasi-compiler-rt
# used by lang/wasi-libcxx
# used by parallel/openmp

LLVM_VERSION=	23.1.3

DISTNAME=	llvm-project-${LLVM_VERSION}.src
MASTER_SITES=	${MASTER_SITE_GITHUB:=llvm/}
GITHUB_PROJECT=	llvm-project
GITHUB_RELEASE=	llvmorg-${PKGVERSION_NOREV}
EXTRACT_SUFX=	.tar.xz

WRKSRC=		${WRKDIR}/${DISTNAME}/${PKGBASE:S/wasi-//}

LLVM_MAJOR_VERSION=	${LLVM_VERSION:tu:C/\\.[[:digit:]\.]*//}

EXTRACT_ELEMENTS=	${DISTNAME}/${PKGBASE:S/wasi-//}
EXTRACT_ELEMENTS+=	${DISTNAME}/cmake
EXTRACT_ELEMENTS+=	${DISTNAME}/runtimes
EXTRACT_ELEMENTS+=	${DISTNAME}/third-party
# LLVM 23 uses libc's header-only common utilities even with runtimes off.
EXTRACT_ELEMENTS+=	${DISTNAME}/libc

.include "../../mk/bsd.prefs.mk"

# This exported profile has prepared only these matching family recipes.
.if ${PKGPATH} != "lang/llvm" && ${PKGPATH} != "lang/clang" && \
    ${PKGPATH} != "devel/lld" && ${PKGPATH} != "devel/py-llvm-lit"
PKG_FAIL_REASON+= "LLVM 23 family consumer ${PKGPATH} is not prepared in the common profile"
.endif

.if ${OPSYS} == "NetBSD" && ${OS_VERSION:M9.*}
# Gcc 8 (induced elsewhere) blows up on per-process VM space.
# Ref. https://mail-index.netbsd.org/pkgsrc-users/2025/06/21/msg041678.html
# Also, the llvm produced by gcc 8 or 10 crashes when building wasi-libc.
GCC_REQD+=	14
.endif
