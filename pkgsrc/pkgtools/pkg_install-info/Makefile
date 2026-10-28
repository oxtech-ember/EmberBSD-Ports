# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), GNU Texinfo standalone Info registrar.
.include "../../devel/gtexinfo/Makefile.common"
# Use the gzip archive of the same release: xz needs libtool, m4 and gmake,
# which need this package to install their Info files.
EXTRACT_SUFX=	.tar.gz

PKGNAME= pkg_install-info-${TEXINFO_VERSION}
PKGREVISION= 2
CATEGORIES= pkgtools
MAINTAINER= pkgsrc-users@NetBSD.org
HOMEPAGE= https://www.gnu.org/software/texinfo/
COMMENT= Standalone GNU info file installation utility
LICENSE= gnu-gpl-v3

USE_LANGUAGES= c
GNU_CONFIGURE= yes
# Build only the registrar and its upstream portability library.
BUILD_DIRS= gnulib/lib install-info
INSTALL_DIRS= install-info
INSTALL_TARGET= install-exec
CONFIGURE_ARGS+= --program-transform-name=s/install-info/pkg_install-info/
CONFIGURE_ARGS+= --disable-nls --disable-perl-xs --disable-perl-tools
# The common C-only mode configures no Perl converter or nested tta tree.
TEST_DIRS= install-info
TEST_TARGET= check

.include "../../mk/bsd.prefs.mk"
.include "../../devel/gtexinfo/cross.mk"

.include "../../mk/bsd.pkg.mk"
