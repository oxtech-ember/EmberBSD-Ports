# $NetBSD: Makefile,v 1.97 2026/08/21 09:38:08 wiz Exp $

.include "Makefile.common"

PKGNAME=	clang-${LLVM_VERSION}
PKGREVISION=	9

# Clear a stale auto-detected value unless a configure input selected one.
.if empty(CMAKE_CONFIGURE_ARGS:M-DHOST_LINK_VERSION*) && \
    empty(CMAKE_CONFIGURE_ARGS.Darwin:M-DHOST_LINK_VERSION*)
CMAKE_CONFIGURE_ARGS.Darwin+= -DHOST_LINK_VERSION:STRING=
.endif
# These installed scripts use Python without linking libpython.
DEPENDS+=	${PYDEPENDENCY}
DEPENDS+=	lld-${LLVM_VERSION}{,nb*}:../../devel/lld
DEPENDS+=	compiler-rt-${LLVM_VERSION}{,nb*}:../../lang/compiler-rt
DEPENDS+=	mksh>=59b:../../shells/mksh

# SDK native-tool contracts pass assembler paths without command arguments.
SUBST_CLASSES+=		clang-as
SUBST_STAGE.clang-as=	pre-configure
SUBST_FILES.clang-as=	clang-as
SUBST_VARS.clang-as=	PREFIX
INSTALLATION_DIRS+=	bin

post-extract:
	${CP} ${FILESDIR}/clang-as.sh ${WRKSRC}/clang-as

post-install: install-clang-as

install-clang-as:
	${INSTALL_SCRIPT} ${WRKSRC}/clang-as ${DESTDIR}${PREFIX}/bin/clang-as

COMMENT=	C language family frontend for LLVM

.if ${USE_CROSS_COMPILE:Uno:tl} == "yes"
# The build interpreter executes on the host. Installed scan-build scripts
# still need the target package and must not contain the host interpreter path.
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
