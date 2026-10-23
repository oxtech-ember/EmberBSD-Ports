# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), selected native documentation executables.
.if !defined(EMBERBSD_KF6_DOCTOOLS_CROSS_MK)
EMBERBSD_KF6_DOCTOOLS_CROSS_MK= yes
.include "../../mk/bsd.prefs.mk"
.if ${USE_CROSS_COMPILE:Uno:tl} == "yes"
.if !defined(EMBERBSD_KF6_DOCTOOLS_HOST)
PKG_FAIL_REASON+= "Set EMBERBSD_KF6_DOCTOOLS_HOST to the current native generator prefix"
.else
CMAKE_CONFIGURE_ARGS+= -DMEINPROC6_EXECUTABLE=${EMBERBSD_KF6_DOCTOOLS_HOST:Q}/bin/meinproc6
CMAKE_CONFIGURE_ARGS+= -DCHECKXML6_EXECUTABLE=${EMBERBSD_KF6_DOCTOOLS_HOST:Q}/bin/checkXML6
CMAKE_CONFIGURE_ARGS+= -DDOCBOOKL10NHELPER_EXECUTABLE=${EMBERBSD_KF6_DOCTOOLS_HOST:Q}/bin/docbookl10nhelper
pre-configure: emberbsd-native-doctools-check
.PHONY: emberbsd-native-doctools-check
emberbsd-native-doctools-check:
	${RUN}${TEST} -r ${EMBERBSD_KF6_HOST_TOOLING:U/nonexistent:Q}/KF6DocTools/KF6DocToolsToolsTargets.cmake && \
	    ${TEST} -f ${EMBERBSD_KF6_DOCTOOLS_HOST:Q}/share/ember-doctools-version && \
	    ${TEST} "`${CAT} ${EMBERBSD_KF6_DOCTOOLS_HOST:Q}/share/ember-doctools-version`" = 6.31.0 && \
	    ${TEST} -x ${EMBERBSD_KF6_DOCTOOLS_HOST:Q}/bin/meinproc6 && \
	    ${TEST} -x ${EMBERBSD_KF6_DOCTOOLS_HOST:Q}/bin/checkXML6 && \
	    ${TEST} -x ${EMBERBSD_KF6_DOCTOOLS_HOST:Q}/bin/docbookl10nhelper || { \
	        echo 'Matching native KDocTools 6.31 generators are required' >&2; exit 1; \
	    }
.endif
.endif
.endif
