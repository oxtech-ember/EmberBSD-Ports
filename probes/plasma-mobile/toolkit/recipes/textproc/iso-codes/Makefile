# $NetBSD: Makefile,v 1.68 2024/02/23 13:31:47 nros Exp $
# Origin: EmberBSD (AI-assisted), current upstream Meson build and host tools.

DISTNAME= iso-codes-4.20.1
CATEGORIES= textproc
MASTER_SITES= https://deb.debian.org/debian/pool/main/i/iso-codes/
DISTFILES= iso-codes_${PKGVERSION_NOREV}.orig.tar.xz
EXTRACT_SUFX= .tar.xz

MAINTAINER= pkgsrc-users@NetBSD.org
HOMEPAGE= https://salsa.debian.org/iso-codes-team/iso-codes
COMMENT= List of country, language and currency names
LICENSE= gnu-lgpl-v2.1

USE_LANGUAGES= # data only
USE_PKGLOCALEDIR= yes
USE_TOOLS+= msgfmt
PYTHON_FOR_BUILD_ONLY= tool
# Upstream's XML generator and UTF-8 test execute only on the build host.
REPLACE_TOOL_PYTHON+= scripts/check_valid_utf8.py scripts/xml_from_json.py

.include "../../lang/python/application.mk"
.include "../../devel/meson/build.mk"
.include "../../mk/bsd.pkg.mk"
