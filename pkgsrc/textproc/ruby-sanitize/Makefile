# $NetBSD$

DISTNAME=	sanitize-7.0.1
CATEGORIES=	textproc

MAINTAINER=	pkgsrc-users@NetBSD.org
HOMEPAGE=	https://github.com/rgrove/sanitize/
COMMENT=	Allowlist-based HTML and CSS sanitizer
LICENSE=	mit

DEPENDS+=	${RUBY_PKGPREFIX}-crass>=1.0.8<1.1:../../www/ruby-crass
DEPENDS+=	${RUBY_PKGPREFIX}-nokogiri>=1.16.8:../../textproc/ruby-nokogiri

USE_LANGUAGES=	# empty

.include "../../lang/ruby/gem.mk"
.include "../../mk/bsd.pkg.mk"
