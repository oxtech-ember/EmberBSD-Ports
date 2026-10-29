# $NetBSD$

DISTNAME=	chef-winrm-fs-1.4.4
CATEGORIES=	net

MAINTAINER=	pkgsrc-users@NetBSD.org
HOMEPAGE=	https://github.com/WinRb/winrm-fs
COMMENT=	WinRM file system (Chef fork of winrm-fs)
LICENSE=	apache-2.0

DEPENDS+=	${RUBY_PKGPREFIX}-chef-winrm>=2.4<3:../../net/ruby-chef-winrm
DEPENDS+=	${RUBY_PKGPREFIX}-csv>=3.3<4:../../textproc/ruby-csv
DEPENDS+=	${RUBY_PKGPREFIX}-erubi>=1.7:../../textproc/ruby-erubi
DEPENDS+=	${RUBY_PKGPREFIX}-logging>=1.6.1<3:../../devel/ruby-logging
DEPENDS+=	${RUBY_PKGPREFIX}-zip>=3.4<4:../../archivers/ruby-zip

USE_LANGUAGES=	# none

RUBYGEM_OPTIONS+=	--format-executable

.include "../../lang/ruby/gem.mk"
.include "../../mk/bsd.pkg.mk"
