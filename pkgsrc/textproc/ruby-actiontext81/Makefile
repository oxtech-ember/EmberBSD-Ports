# $NetBSD$

DISTNAME=	actiontext-${RAILS_VERSION}
PKGNAME=	${RUBY_PKGPREFIX}-actiontext${RUBY_RAILS}-${RAILS_VERSION}
CATEGORIES=	textproc devel

MAINTAINER=	pkgsrc-users@NetBSD.org
HOMEPAGE=	http://www.rubyonrails.org/
COMMENT=	Rich text framework (for Rails 8.1)
LICENSE=	mit

DEPENDS+=	${RUBY_ACTIVESTORAGE_DEPENDS}
DEPENDS+=	${RUBY_PKGPREFIX}-nokogiri>=1.8.5:../../textproc/ruby-nokogiri
DEPENDS+=	${RUBY_PKGPREFIX}-action_text-trix>=2.1.15<2.2:../../www/ruby-action_text-trix
#DEPENDS+=	${RUBY_PKGPREFIX}-globalid>=0.3.6:../../devel/ruby-globalid

USE_LANGUAGES=	# none

RUBY_RAILS_ACCEPTED=	81
RUBY_RAILS_STRICT_DEP=	yes

.include "../../lang/ruby/gem.mk"
.include "../../mk/bsd.pkg.mk"
