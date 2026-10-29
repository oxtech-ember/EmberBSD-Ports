# $NetBSD$

DISTNAME=	json_schemer-2.5.0
CATEGORIES=	textproc

MAINTAINER=	pkgsrc-users@NetBSD.org
HOMEPAGE=	https://github.com/davishmcclurg/json_schemer
COMMENT=	JSON Schema validator
LICENSE=	mit

DEPENDS+=	${RUBY_PKGPREFIX}-hana>=1.3<2:../../devel/ruby-hana
DEPENDS+=	${RUBY_PKGPREFIX}-regexp_parser>=2.0<3:../../devel/ruby-regexp_parser
DEPENDS+=	${RUBY_PKGPREFIX}-simpleidn>=0.2<0.3:../../devel/ruby-simpleidn

USE_LANGUAGES=	# none

.include "../../lang/ruby/gem.mk"
.include "../../mk/bsd.pkg.mk"
