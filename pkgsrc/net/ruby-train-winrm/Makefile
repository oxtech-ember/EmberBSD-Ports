# $NetBSD$

DISTNAME=	train-winrm-0.4.3
CATEGORIES=	net

MAINTAINER=	pkgsrc-users@NetBSD.org
HOMEPAGE=	https://github.com/inspec/train-winrm
COMMENT=	Windows WinRM API Transport for Train
LICENSE=	apache-2.0

DEPENDS+=	${RUBY_PKGPREFIX}-chef-winrm>=2.4.4<3:../../net/ruby-chef-winrm
DEPENDS+=	${RUBY_PKGPREFIX}-chef-winrm-elevated>=1.2.5<2:../../net/ruby-chef-winrm-elevated
DEPENDS+=	${RUBY_PKGPREFIX}-chef-winrm-fs>=1.4.1<2:../../net/ruby-chef-winrm-fs
DEPENDS+=	${RUBY_PKGPREFIX}-socksify>=1.8<2:../../net/ruby-socksify

USE_LANGUAGES=	# none

.include "../../lang/ruby/gem.mk"
.include "../../mk/bsd.pkg.mk"
