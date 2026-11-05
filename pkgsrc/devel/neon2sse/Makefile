# Origin: EmberBSD contributors (AI-assisted); upstream shared source owner.
DISTNAME= neon2sse-78784fefa872994ea9acbb7371d3003884815116
PKGNAME= neon2sse-source-0.0.20261026
CATEGORIES= devel
MASTER_SITES= -https://github.com/intel/ARM_NEON_2_x86_SSE/archive/78784fefa872994ea9acbb7371d3003884815116.tar.gz
WRKSRC= ${WRKDIR}/ARM_NEON_2_x86_SSE-78784fefa872994ea9acbb7371d3003884815116
HOMEPAGE= https://github.com/intel/ARM_NEON_2_x86_SSE
COMMENT= Shared neon2sse upstream source for SDK consumers
LICENSE= bsd-source-code
NO_ARCH= yes
NO_BUILD= yes
NO_CONFIGURE= yes
USE_LANGUAGES= # source only
USE_TOOLS+= find sort tar
CHECK_INTERPRETER_SKIP+= share/neon2sse-source/*

do-install:
	${INSTALL_DATA_DIR} ${DESTDIR:Q}${PREFIX:Q}/share/neon2sse-source
	${TAR} -cf ${WRKDIR:Q}/neon2sse-source.tar -C ${WRKSRC:Q} .
	${TAR} -xf ${WRKDIR:Q}/neon2sse-source.tar -C ${DESTDIR:Q}${PREFIX:Q}/share/neon2sse-source

GENERATE_PLIST+= cd ${DESTDIR:Q}${PREFIX:Q}; ${FIND} share/neon2sse-source \( -type f -o -type l \) -print | ${SORT};
.include "../../mk/bsd.pkg.mk"
