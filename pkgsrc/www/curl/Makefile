# $NetBSD: Makefile,v 1.309 2026/09/02 19:19:31 wiz Exp $

PREFER.openssl=	pkgsrc

.include "Makefile.common"
PKGREVISION=	2

CONFIGURE_ARGS+=	--with-ssl=${_CROSS_DESTDIR:U}${BUILDLINK_PREFIX.openssl}

SUBST_CLASSES+=		rpath
SUBST_FILES.rpath+=	curl-config.in
SUBST_SED.rpath+=	-e 's!-L@libdir@!${COMPILER_RPATH_FLAG}@libdir@ -L@libdir@!'
SUBST_STAGE.rpath=	pre-configure
SUBST_MESSAGE.rpath=	Adding rpath to curl-config.

SUPERSEDES+=		wcurl-[0-9]*

.include "options.mk"

# 8.22.0
# TESTDONE: 2072 tests were considered during 655 seconds.
# TESTDONE: 1623 tests out of 1623 reported OK: 100%

# Development metadata is consumed on the target after cross installation.
.if ${USE_CROSS_COMPILE:Uno:tl} == "yes" && ${EMBERBSD_COMMON_TOOLS:Uno} == "yes"
post-install: ember-curl-cross-metadata
.PHONY: ember-curl-cross-metadata
ember-curl-cross-metadata:
	${RUN}set -e; for file in ${DESTDIR}${PREFIX}/bin/curl-config \
	    ${DESTDIR}${PREFIX}/lib/pkgconfig/libcurl.pc; do \
		${CP} -p "$$file" "$$file.ember"; \
		${AWK} -v root=${CROSS_DESTDIR:Q} -v triplet=${MACHINE_GNU_PLATFORM:Q} \
		    -v target=${PREFIX:Q}/gcc16/bin/gcc \
		    'function repl(s,a,b, n,t) { if (a=="") return s; t=""; while ((n=index(s,a)) != 0) { t=t substr(s,1,n-1) b; s=substr(s,n+length(a)); } return t s; } \
		    { line=repl($$0,root,""); if (line ~ /^[[:space:]]*echo / && index(line,triplet "-gcc") != 0 && line !~ /--build=/) line=repl(line,triplet "-gcc",target); print line; }' \
		    "$$file" > "$$file.ember"; \
		${MV} -f "$$file.ember" "$$file"; \
	done
.endif

.include "../../mk/bsd.pkg.mk"
