# $NetBSD$

DISTNAME=	jirametrics-3.5
CATEGORIES=	devel

MAINTAINER=	schmonz@NetBSD.org
HOMEPAGE=	https://jirametrics.org/
COMMENT=	Export Jira data and generate reports
LICENSE=	apache-2.0

DEPENDS+=	${RUBY_PKGPREFIX}-csv>=3.3:../../textproc/ruby-csv
DEPENDS+=	${RUBY_PKGPREFIX}-json-schema>=6.2:../../textproc/ruby-json-schema
DEPENDS+=	${RUBY_PKGPREFIX}-mcp>=1.8:../../devel/ruby-mcp
DEPENDS+=	${RUBY_PKGPREFIX}-random-word>=2.1.1<2.2:../../textproc/ruby-random-word
DEPENDS+=	${RUBY_PKGPREFIX}-require_all>=3.0.0<3.1:../../devel/ruby-require_all
DEPENDS+=	${RUBY_PKGPREFIX}-thor>=0:../../devel/ruby-thor

USE_LANGUAGES=	# none

.include "../../lang/ruby/gem.mk"
.include "../../mk/bsd.pkg.mk"
