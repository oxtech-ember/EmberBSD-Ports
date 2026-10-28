# $NetBSD$
DISTNAME= HdrHistogram_c-0.12.1
PKGNAME= hdr-histogram-0.12.1
WRKSRC= ${WRKDIR}/${DISTNAME}
CATEGORIES= devel
MASTER_SITES= ${MASTER_SITE_GITHUB:=HdrHistogram/}
GITHUB_PROJECT= HdrHistogram_c
GITHUB_TAG= ${PKGVERSION_NOREV}
HOMEPAGE= https://github.com/HdrHistogram/HdrHistogram_c
COMMENT= High dynamic range histograms for C
LICENSE= 2-clause-bsd OR cc0-1.0-universal
USE_LANGUAGES= c c++
TEST_TARGET= test
HDR_BENCHMARKS?= no
PLIST_VARS+= benchmark
.if ${HDR_BENCHMARKS:tl} == "yes"
CMAKE_CONFIGURE_ARGS+= -DHDR_HISTOGRAM_BUILD_BENCHMARK=ON
PLIST.benchmark= yes
.include "../../benchmarks/google-benchmark/buildlink3.mk"
.endif
BUILDLINK_PASSTHRU_RPATHDIRS+= ${WRKDIR}/${DISTNAME}/cmake-pkgsrc-build/src
.include "../../mk/bsd.prefs.mk"
.if ${OPSYS} == "Darwin"
HDR_LIB= libhdr_histogram.dylib
HDR_SOVERSION= libhdr_histogram.6.dylib
HDR_VERSIONED= libhdr_histogram.6.5.4.dylib
.else
HDR_LIB= libhdr_histogram.so
HDR_SOVERSION= libhdr_histogram.so.6
HDR_VERSIONED= libhdr_histogram.so.6.5.4
.endif
PLIST_SUBST+= HDR_LIB=${HDR_LIB} HDR_SOVERSION=${HDR_SOVERSION} HDR_VERSIONED=${HDR_VERSIONED}
GENERATE_PLIST+= cd ${DESTDIR}${PREFIX}; ${FIND} lib/cmake/hdr_histogram -name "hdr_histogram-targets-*.cmake" -type f -print | ${SORT};
.include "../../devel/zlib/buildlink3.mk"
.include "../../devel/cmake/build.mk"
.include "../../mk/bsd.pkg.mk"
