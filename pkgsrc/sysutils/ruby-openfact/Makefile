# $NetBSD$

DISTNAME=	openfact-6.2.3
PKGREVISION=	1
CATEGORIES=	sysutils

MAINTAINER=	pkgsrc-users@NetBSD.org
HOMEPAGE=	https://github.com/OpenVoxProject/openfact
COMMENT=	Cross-platform Ruby library for retrieving facts from OS (Facter fork)
LICENSE=	apache-2.0

.include "../../mk/bsd.prefs.mk"

.if ${OPSYS} == "NetBSD" && ${MACHINE_ARCH} == "aarch64"
# The BSD sysctl resolver needs the AArch64 typedef table.
DEPENDS+=	${RUBY_PKGPREFIX}-ffi>=1.17.4nb1<1.18.0:../../devel/ruby-ffi
.else
DEPENDS+=	${RUBY_PKGPREFIX}-ffi{>=1.15.5<1.16.0,>=1.16.3<1.18.0}:../../devel/ruby-ffi
.endif
DEPENDS+=	${RUBY_PKGPREFIX}-hocon>=1.3<2:../../devel/ruby-hocon
DEPENDS+=	${RUBY_PKGPREFIX}-thor>=1.5<2:../../devel/ruby-thor

# The CPU, load average and hostname resolvers load ffi at run time.
SUBST_CLASSES+=		ffi
SUBST_STAGE.ffi=	pre-configure
SUBST_FILES.ffi=	../${DISTNAME}.gemspec
SUBST_SED.ffi=		-e '/add_development_dependency.*[<"]ffi[>"]/s/add_development_dependency/add_runtime_dependency/'

RUBYGEM_OPTIONS+=	--format-executable

.include "../../lang/ruby/gem.mk"
.include "../../mk/bsd.pkg.mk"
