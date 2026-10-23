# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), GNU Texinfo standalone Info registrar.
.include "../../devel/gtexinfo/Makefile.common"

PKGNAME= pkg_install-info-${TEXINFO_VERSION}
CATEGORIES= pkgtools
MAINTAINER= pkgsrc-users@NetBSD.org
HOMEPAGE= https://www.gnu.org/software/texinfo/
COMMENT= Standalone GNU info file installation utility
LICENSE= gnu-gpl-v3

USE_LANGUAGES= c
USE_TOOLS+= gmake perl:build
GNU_CONFIGURE= yes
# Build only the registrar and its upstream portability library.
BUILD_DIRS= gnulib/lib install-info
INSTALL_DIRS= install-info
INSTALL_TARGET= install-exec
CONFIGURE_ARGS+= --program-transform-name=s/install-info/pkg_install-info/
CONFIGURE_ARGS+= --disable-nls --disable-perl-xs
TEST_DIRS= install-info
TEST_TARGET= check

.include "../../mk/bsd.prefs.mk"
.include "../../devel/gtexinfo/cross.mk"

.include "../../mk/bsd.pkg.mk"
