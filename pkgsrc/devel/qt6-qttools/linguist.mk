# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Translation generators execute on the host.
# Include only for consumers of Linguist tools, not QtTools target libraries.
.if !defined(EMBERBSD_QT_LINGUIST_MK)
EMBERBSD_QT_LINGUIST_MK= yes
.include "../../mk/bsd.prefs.mk"
.include "../../x11/qt6-qtbase/native-runtime.mk"
.if defined(EMBERBSD_QT_HOST_PATH) && !empty(EMBERBSD_QT_HOST_PATH)
CMAKE_CONFIGURE_ARGS+= -DQt6LinguistTools_DIR=${EMBERBSD_QT_HOST_PATH:Q}/lib/cmake/Qt6LinguistTools
pre-configure: emberbsd-native-linguist-check
.PHONY: emberbsd-native-linguist-check
emberbsd-native-linguist-check:
	${RUN}${TEST} -x ${EMBERBSD_QT_HOST_PATH:Q}/bin/lconvert && \
	    ${TEST} "`${_EMBERBSD_QT_RUNTIME_EXEC} ${EMBERBSD_QT_HOST_PATH:Q}/bin/lrelease -version`" = "lrelease version 6.12.0" || { \
	        echo 'Matching native Qt 6.12 Linguist tools are required' >&2; exit 1; \
	    }
.elif ${USE_CROSS_COMPILE:Uno:tl} == "yes"
PKG_FAIL_REASON+= "Cross Linguist consumers require matching EMBERBSD_QT_HOST_PATH"
.else
BUILDLINK_DEPMETHOD.qt6-qttools?= build
.include "../../devel/qt6-qttools/buildlink3.mk"
.endif
.endif
