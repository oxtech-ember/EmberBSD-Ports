# $NetBSD$

DISTNAME=	chef-winrm-elevated-1.2.5
CATEGORIES=	net

MAINTAINER=	pkgsrc-users@NetBSD.org
HOMEPAGE=	https://github.com/chef/chef-winrm-elevated
COMMENT=	Run PowerShell as an elevated user over WinRM (Chef fork)
LICENSE=	apache-2.0

DEPENDS+=	${RUBY_PKGPREFIX}-chef-winrm>=2.3.11:../../net/ruby-chef-winrm
DEPENDS+=	${RUBY_PKGPREFIX}-chef-winrm-fs>=1.3.7:../../net/ruby-chef-winrm-fs
DEPENDS+=	${RUBY_PKGPREFIX}-erubi>=1.8<2:../../textproc/ruby-erubi

USE_LANGUAGES=	# none

.include "../../lang/ruby/gem.mk"
.include "../../mk/bsd.pkg.mk"
