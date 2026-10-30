# $NetBSD: version.mk,v 1.22 2026/09/02 20:22:38 adam Exp $
# used by devel/lld
# used by devel/lldb
# used by devel/polly
# used by lang/clang
# used by lang/clang-tools-extra
# used by lang/compiler-rt
# used by lang/flang
# used by lang/flang-rt
# used by lang/libclc
# used by lang/libcxx
# used by lang/libcxxabi
# used by lang/libunwind
# used by lang/mlir
# used by lang/wasi-compiler-rt
# used by lang/wasi-libcxx
# used by parallel/openmp

LLVM_VERSION=	23.1.4

DISTNAME=	llvm-project-${LLVM_VERSION}.src
MASTER_SITES=	https://github.com/llvm/llvm-project/releases/download/llvmorg-${LLVM_VERSION}/
EXTRACT_SUFX=	.tar.xz

WRKSRC=		${WRKDIR}/${DISTNAME}/${PKGBASE:S/wasi-//:S/llvm-devel/llvm/}

LLVM_MAJOR_VERSION=	${LLVM_VERSION:tu:C/\\.[[:digit:]\.]*//}

EXTRACT_ELEMENTS=	${DISTNAME}/${PKGBASE:S/wasi-//:S/llvm-devel/llvm/}
EXTRACT_ELEMENTS+=	${DISTNAME}/cmake
EXTRACT_ELEMENTS+=	${DISTNAME}/runtimes
EXTRACT_ELEMENTS+=	${DISTNAME}/third-party
# LLVM 23 uses libc's header-only common utilities even with runtimes off.
EXTRACT_ELEMENTS+=	${DISTNAME}/libc

.include "../../mk/bsd.prefs.mk"

# This exported profile has prepared only these matching family recipes.
.if ${PKGPATH} != "lang/llvm" && ${PKGPATH} != "lang/llvm-devel" && ${PKGPATH} != "lang/clang" && \
    ${PKGPATH} != "devel/lld" && ${PKGPATH} != "devel/py-llvm-lit" && ${PKGPATH} != "lang/compiler-rt" && \
    ${PKGPATH} != "lang/mlir" && ${PKGPATH} != "lang/flang" && ${PKGPATH} != "lang/flang-rt" && \
    ${PKGPATH} != "lang/libcxx" && ${PKGPATH} != "lang/libcxx-devel" && \
    ${PKGPATH} != "lang/libcxxabi" && ${PKGPATH} != "lang/libcxxabi-devel" && \
    ${PKGPATH} != "lang/libunwind" && ${PKGPATH} != "lang/libunwind-devel" && ${PKGPATH} != "lang/wasi-compiler-rt" && \
    ${PKGPATH} != "lang/wasi-libc" && ${PKGPATH} != "lang/riscv32-elf-compiler-rt" && \
    ${PKGPATH} != "lang/llvm-libc-source" && \
    ${PKGPATH} != "lang/clang-python-bindings" && \
    ${PKGPATH} != "devel/lldb"
PKG_FAIL_REASON+= "LLVM 23 family consumer ${PKGPATH} is not prepared in the common profile"
.endif

