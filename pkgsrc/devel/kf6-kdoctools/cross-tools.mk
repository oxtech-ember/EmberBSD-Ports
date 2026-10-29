# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), native documentation generators.
.if !defined(EMBERBSD_KF6_DOCTOOLS_CROSS_MK)
EMBERBSD_KF6_DOCTOOLS_CROSS_MK= yes
.include "../../mk/bsd.prefs.mk"
.if ${USE_CROSS_COMPILE:Uno:tl} == "yes"
# meinproc6, checkXML6 and docbookl10nhelper run on the build host. They come
# from devel/kf6-kdoctools-generators, a native package of the same release.
_EMBER_KF6_DOCTOOLS_VERSION=	6.31.0
TOOL_DEPENDS+=	kf6-kdoctools-generators-${_EMBER_KF6_DOCTOOLS_VERSION}{,nb[0-9]*}:../../devel/kf6-kdoctools-generators
_EMBER_KF6_DOCTOOLS_CMAKE=	${TOOLBASE}/lib/cmake/KF6DocTools
CMAKE_CONFIGURE_ARGS+= -DKDOCTOOLS_TARGETSFILE=${_EMBER_KF6_DOCTOOLS_CMAKE:Q}/KF6DocToolsToolsTargets.cmake
CMAKE_CONFIGURE_ARGS+= -DMEINPROC6_EXECUTABLE=${TOOLBASE:Q}/bin/meinproc6
CMAKE_CONFIGURE_ARGS+= -DCHECKXML6_EXECUTABLE=${TOOLBASE:Q}/bin/checkXML6
CMAKE_CONFIGURE_ARGS+= -DDOCBOOKL10NHELPER_EXECUTABLE=${TOOLBASE:Q}/bin/docbookl10nhelper
pre-configure: emberbsd-native-doctools-check
.PHONY: emberbsd-native-doctools-check
emberbsd-native-doctools-check:
	${RUN}${TEST} -r ${_EMBER_KF6_DOCTOOLS_CMAKE:Q}/KF6DocToolsToolsTargets.cmake && \
	    ${GREP} -q 'set(PACKAGE_VERSION "${_EMBER_KF6_DOCTOOLS_VERSION}")' \
	        ${_EMBER_KF6_DOCTOOLS_CMAKE:Q}/KF6DocToolsConfigVersion.cmake && \
	    ${TEST} -x ${TOOLBASE:Q}/bin/meinproc6 && \
	    ${TEST} -x ${TOOLBASE:Q}/bin/checkXML6 && \
	    ${TEST} -x ${TOOLBASE:Q}/bin/docbookl10nhelper || { \
	        echo 'Matching native KDocTools 6.31 generators are required' >&2; exit 1; \
	    }
.endif
.endif
