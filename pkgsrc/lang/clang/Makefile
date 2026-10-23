# $NetBSD: Makefile,v 1.97 2026/08/21 09:38:08 wiz Exp $

.include "Makefile.common"

PKGNAME=	clang-${LLVM_VERSION}
PKGREVISION=	1
# These installed scripts use Python without linking libpython.
DEPENDS+=	${PYDEPENDENCY}

COMMENT=	C language family frontend for LLVM

.if ${USE_CROSS_COMPILE:Uno:tl} == "yes"
# The build interpreter executes on the host. Installed scan-build scripts
# still need the target package and must not contain the host interpreter path.
EMBERBSD_CROSS_BUILD_PERL?= ${TOOLBASE}/bin/perl
.if empty(EMBERBSD_CROSS_BUILD_PERL:M/*) || !exists(${EMBERBSD_CROSS_BUILD_PERL})
PKG_FAIL_REASON+= "Set EMBERBSD_CROSS_BUILD_PERL to the current host Perl"
.else
_EMBERBSD_CLANG_HOST_PERL!= if test -x ${EMBERBSD_CROSS_BUILD_PERL:Q}; then \
    ${EMBERBSD_CROSS_BUILD_PERL:Q} -e 'print($$] >= 5.044 ? "yes" : "no")'; fi
.if ${_EMBERBSD_CLANG_HOST_PERL:U} != yes
PKG_FAIL_REASON+= "The Clang cross build needs host Perl 5.44.0 or newer"
.endif
.endif
USE_TOOLS+= perl
TOOLS_IGNORE.perl=
TOOLS_PATH.perl= ${EMBERBSD_CROSS_BUILD_PERL}
DEPENDS+= perl>=5.44.0:../../lang/perl5
REPLACE_INTERPRETER+= target-perl
REPLACE.target-perl.old= .*perl[^[:space:]]*
REPLACE.target-perl.new= ${PREFIX}/bin/perl
REPLACE_FILES.target-perl:= ${REPLACE_PERL}
REPLACE_PERL=
.else
USE_TOOLS+= perl:run
.endif

# Certain header files are generated, and can only be generated
# if llvm has support for the target.
PLIST_VARS+=	RISCV
.if ${PKG_BUILD_OPTIONS.llvm:Mllvm-target-riscv}
PLIST.RISCV=	yes
.endif

PLIST_VARS+=	ARM
.if	${PKG_BUILD_OPTIONS.llvm:Mllvm-target-arm} ||	\
	${PKG_BUILD_OPTIONS.llvm:Mllvm-target-aarch64}
PLIST.ARM=	yes
.endif

# libclang-cpp.so uses connect(), socket(), ...
LDFLAGS.SunOS+=	-lsocket

.include "../../mk/atomic64.mk"
.include "../../mk/bsd.pkg.mk"
