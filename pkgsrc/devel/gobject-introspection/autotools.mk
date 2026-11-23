# SPDX-License-Identifier: BSD-2-Clause
# Cross Autotools builds need make rules and generators from the native GI package.
.include "../../mk/bsd.prefs.mk"
.if ${USE_CROSS_COMPILE:Uno:tl} == "yes"
EMBERBSD_GI_MESON_OPTIONS= no
.include "../../devel/gobject-introspection/cross.mk"
MAKE_FLAGS+= INTROSPECTION_MAKEFILE=${TOOLBASE:Q}/share/gobject-introspection-1.0/Makefile.introspection
MAKE_FLAGS+= INTROSPECTION_SCANNER=${WRKDIR:Q}/.meson-gi-scanner
MAKE_FLAGS+= INTROSPECTION_COMPILER=${_EMBER_GI_COMPILER:Q}
.endif
