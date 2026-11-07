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
# Qt's pkg-config files live in qt6/lib/pkgconfig. Meson searches the
# buildlink lib/pkgconfig directory. The links stay inside this build.
pre-configure: appstream-qt-pkgconfig
appstream-qt-pkgconfig:
	cd ${BUILDLINK_DIR}/qt6/lib/pkgconfig && \
	    for pc in *.pc; do \
		${LN} -sf ${BUILDLINK_DIR}/qt6/lib/pkgconfig/$$pc \
		    ${BUILDLINK_DIR}/lib/pkgconfig/$$pc; \
	    done
# Meson 1.12 runs moc from the target Qt prefix and stops when that ELF
# exists. Leave the sysroot files in place. qt/meson.build reads this
# build-machine property and runs the Ports SDK host moc instead.
.if ${USE_CROSS_COMPILE:Uno:tl} == "yes"
MESON_ARGS+=		--native-file ${WRKDIR}/.qt-host
pre-configure: appstream-qt-host-moc
appstream-qt-host-moc:
	${PRINTF} '%s\n' '[properties]' \
	    "qt_host_moc = '${EMBERBSD_HOST_PREFIX}/qt6/libexec/moc'" \
	    > ${WRKDIR}/.qt-host
.endif
.else
MESON_ARGS+=	-Dqt=false
.endif
