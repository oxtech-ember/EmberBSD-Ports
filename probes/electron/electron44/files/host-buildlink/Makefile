# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
# Minimal native pkgsrc consumer; the dependency declaration belongs to Electron.
DISTNAME= electron-host-buildlink-0
CATEGORIES= devel
DISTFILES= # none
COMMENT= Electron build-host dependency selection
LICENSE= mit
NO_BUILD= yes
NO_CONFIGURE= yes
NO_INSTALL= yes
USE_LANGUAGES= c c++

.if !defined(EMBERBSD_ELECTRON_HOST_DEPENDENCIES) || empty(EMBERBSD_ELECTRON_HOST_DEPENDENCIES:M/*)
PKG_FAIL_REASON+= "Select the Electron host dependency declaration"
.else
.include "${EMBERBSD_ELECTRON_HOST_DEPENDENCIES}"
.endif
.include "../../mk/bsd.pkg.mk"
