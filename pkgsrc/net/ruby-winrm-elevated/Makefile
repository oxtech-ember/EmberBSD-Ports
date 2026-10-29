# $NetBSD$

DISTNAME=	winrm-elevated-1.2.4
CATEGORIES=	net

MAINTAINER=	pkgsrc-users@NetBSD.org
HOMEPAGE=	https://github.com/WinRb/winrm-elevated
COMMENT=	Ruby library for running commands as elevated
LICENSE=	mit

#DEPENDS+=	${RUBY_PKGPREFIX}-winrm>=2.0<3:../../net/net/ruby-winrm
DEPENDS+=	${RUBY_PKGPREFIX}-winrm>=2.0<3:../../net/ruby-winrm
DEPENDS+=	${RUBY_PKGPREFIX}-winrm-fs>=1.0<2:../../net/ruby-winrm-fs

USE_LANGUAGES=	# none

.include "../../lang/ruby/gem.mk"
.include "../../mk/bsd.pkg.mk"
