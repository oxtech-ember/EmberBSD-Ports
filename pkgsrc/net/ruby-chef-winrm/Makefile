# $NetBSD$

DISTNAME=	chef-winrm-2.5.0
CATEGORIES=	net

MAINTAINER=	pkgsrc-users@NetBSD.org
HOMEPAGE=	https://github.com/WinRb/WinRM
COMMENT=	Ruby library for Windows Remote Management (Chef fork)
LICENSE=	apache-2.0

DEPENDS+=	${RUBY_PKGPREFIX}-builder>=2.1.2:../../textproc/ruby-builder
DEPENDS+=	${RUBY_PKGPREFIX}-chef-gyoku>=1.5<2:../../textproc/ruby-chef-gyoku
DEPENDS+=	${RUBY_PKGPREFIX}-erubi>=1.8<2:../../textproc/ruby-erubi
DEPENDS+=	${RUBY_PKGPREFIX}-gssapi>=1.2<2:../../security/ruby-gssapi
DEPENDS+=	${RUBY_PKGPREFIX}-httpclient>=2.2.0.2<3:../../www/ruby-httpclient
DEPENDS+=	${RUBY_PKGPREFIX}-logging>=1.6.1<3:../../devel/ruby-logging
DEPENDS+=	${RUBY_PKGPREFIX}-nori>=2.7<3:../../textproc/ruby-nori
DEPENDS+=	${RUBY_PKGPREFIX}-rubyntlm>=0.6.3<0.7:../../security/ruby-rubyntlm

USE_LANGUAGES=	# none

RUBYGEM_OPTIONS+=	--format-executable

.include "../../lang/ruby/gem.mk"
.include "../../mk/bsd.pkg.mk"
