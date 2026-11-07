# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
# Discover 6.8 requires the AppStreamQt library from this recipe.

PKG_OPTIONS_VAR=	PKG_OPTIONS.appstream
PKG_SUPPORTED_OPTIONS=	qt
PKG_SUGGESTED_OPTIONS=	qt

.include "../../mk/bsd.options.mk"

PLIST_VARS+=	qt gir man

.if !empty(PKG_OPTIONS:Mqt)
PLIST.qt=	yes
MESON_ARGS+=	-Dqt=true
.include "../../x11/qt6-qtbase/buildlink3.mk"
# lrelease, moc and rcc must be the host Qt tools. The sysroot copies are
# NetBSD binaries and cannot run while cross-building. Meson probes the
# plain tool name on PATH after the target file is absent.
CONFIGURE_ENV+=	PATH=${EMBERBSD_HOST_PREFIX}/qt6/libexec:${EMBERBSD_HOST_PREFIX}/qt6/bin:${PATH}
MAKE_ENV+=	PATH=${EMBERBSD_HOST_PREFIX}/qt6/libexec:${EMBERBSD_HOST_PREFIX}/qt6/bin:${PATH}
MESON_ARGS+=	--cross-file ${WRKDIR}/.qt-cross
# Qt's pkg-config files live in qt6/lib/pkgconfig. Meson only searches
# the buildlink lib/pkgconfig directory.
pre-configure: appstream-qt-pkgconfig
appstream-qt-pkgconfig:
	cd ${BUILDLINK_DIR}/qt6/lib/pkgconfig && \
	    for pc in *.pc; do \
		${LN} -sf ${BUILDLINK_DIR}/qt6/lib/pkgconfig/$$pc \
		    ${BUILDLINK_DIR}/lib/pkgconfig/$$pc; \
	    done
	${PRINTF} '%s\n' '[binaries]' > ${WRKDIR}/.qt-cross
	for tool in ${EMBERBSD_HOST_PREFIX}/qt6/libexec/* \
	    ${EMBERBSD_HOST_PREFIX}/qt6/bin/lrelease \
	    ${EMBERBSD_HOST_PREFIX}/qt6/bin/lupdate \
	    ${EMBERBSD_HOST_PREFIX}/qt6/bin/qmake \
	    ${EMBERBSD_HOST_PREFIX}/qt6/bin/qmake6; do \
		if ${TEST} -x "$$tool"; then \
		    ${PRINTF} "%s = '%s'\n" "$${tool##*/}" "$$tool" \
			>> ${WRKDIR}/.qt-cross; \
		fi; \
	done
.else
MESON_ARGS+=	-Dqt=false
.endif
