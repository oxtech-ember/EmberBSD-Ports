# $NetBSD: Makefile,v 1.60 2026/01/22 21:00:42 adam Exp $

DISTNAME=	tdb-1.4.15
PKGREVISION=	2
CATEGORIES=	databases
MASTER_SITES=	https://www.samba.org/ftp/tdb/

MAINTAINER=	pkgsrc-users@NetBSD.org
HOMEPAGE=	https://tdb.samba.org/
COMMENT=	Small database system which uses files to store data
LICENSE=	gnu-gpl-v3

TOOL_DEPENDS+=	libxslt-[0-9]*:../../textproc/libxslt
TOOL_DEPENDS+=	docbook-xsl-[0-9]*:../../textproc/docbook-xsl

# both install tdbtool and tdbdump
CONFLICTS+=	samba<3.6.6nb3

USE_TOOLS+=		gmake
HAS_CONFIGURE=		yes
CONFIGURE_ARGS+=	--mandir=${PREFIX}/${PKGMANDIR}
CONFIGURE_ARGS+=	--abi-check-disable
CONFIGURE_ARGS+=	--disable-symbol-versions
# Waf otherwise adds /usr/local to every compile/link search after iconv
# detection. pkgsrc supplies the selected builtin or buildlink paths instead.
CONFIGURE_ARGS+=	--with-libiconv=
.if defined(MAKE_JOBS) && !empty(MAKE_JOBS) && !(defined(MAKE_JOBS_SAFE) && ${MAKE_JOBS_SAFE:U:tl} == no)
CONFIGURE_ARGS+=	--jobs=${MAKE_JOBS}
.else
CONFIGURE_ARGS+=	--jobs=1
.endif
PKGCONFIG_OVERRIDE=	tdb.pc.in
TEST_TARGET=		test

USE_GCC_RUNTIME=	yes

PY_PATCHPLIST=		yes
REPLACE_TOOL_PYTHON+=	buildtools/bin/waf
MAKE_FLAGS+=		WAF_BINARY=${TOOL_PYTHONBIN}\ ${WRKSRC}/buildtools/bin/waf

SUBST_CLASSES+=		docbook
SUBST_MESSAGE.docbook=	Fixing docbook URLs.
SUBST_FILES.docbook+=	buildtools/wafsamba/samba_conftests.py
SUBST_FILES.docbook+=	buildtools/wafsamba/wafsamba.py
SUBST_STAGE.docbook=	pre-configure
SUBST_SED.docbook+=	-e 's,http://docbook.sourceforge.net/release/xsl/current,${TOOLBASE}/share/xsl/docbook,g'

.include "../../mk/bsd.prefs.mk"
.if ${USE_CROSS_COMPILE:Uno:tl} == "yes"
# Waf runs on the host; its compiled feature probes run on the EmberBSD target.
.for _input in EMBERBSD_CROSS_BUILD_PYTHON EMBERBSD_GI_QUERY_CONFIG
.if empty(${_input}:M/*) || !empty(${_input}:C/[A-Za-z0-9_.\/-]//g) || !exists(${${_input}})
PKG_FAIL_REASON+= "${_input} must name an existing absolute file without shell metacharacters"
.endif
.endfor
.if empty(EMBERBSD_SDK_SOURCE:M/*) || !empty(EMBERBSD_SDK_SOURCE:C/[A-Za-z0-9_.\/-]//g) || !exists(${EMBERBSD_SDK_SOURCE}/src/emberbsd_sdk/__init__.py)
PKG_FAIL_REASON+= "EMBERBSD_SDK_SOURCE must name an absolute SDK source directory without shell metacharacters"
.endif
EMBERBSD_TDB_QUERY= ${.CURDIR}/../../devel/gobject-introspection/files/target-query.py
EMBERBSD_TDB_EXECUTOR= ${EMBERBSD_CROSS_BUILD_PYTHON} -E -S ${EMBERBSD_TDB_QUERY} --execute
CONFIGURE_ARGS+= --cross-compile --cross-execute=${EMBERBSD_TDB_EXECUTOR:Q}
CONFIGURE_ENV+= EMBERBSD_SDK_SOURCE=${EMBERBSD_SDK_SOURCE:Q}
CONFIGURE_ENV+= EMBERBSD_GI_TARGET=${MACHINE_ARCH:S/x86_64/amd64/}
CONFIGURE_ENV+= EMBERBSD_GI_QUERY_CONFIG=${EMBERBSD_GI_QUERY_CONFIG:Q}
CONFIGURE_ENV+= EMBERBSD_GI_FAILURE_MARKER=${WRKDIR}/.tdb-query-failure
CONFIGURE_ENV+= PYTHON=${TOOL_PYTHONBIN:Q}
# Reuse pkgsrc's target sysconfig environment during configure as well as make.
# Execute the target python-config script with the host interpreter.
CONFIGURE_ENV+= PYTHONPATH=${WRKDIR}/.pysite:${CROSS_DESTDIR}${LOCALBASE}/${PYLIB}
CONFIGURE_ENV+= PYTHON_CONFIG=${TOOL_PYTHONBIN:Q}\ ${CROSS_DESTDIR}${PYTHONBIN}-config
pre-configure: emberbsd-tdb-query
.PHONY: emberbsd-tdb-query
emberbsd-tdb-query:
	${RUN}${SETENV} EMBERBSD_SDK_SOURCE=${EMBERBSD_SDK_SOURCE:Q} EMBERBSD_GI_QUERY_CONFIG=${EMBERBSD_GI_QUERY_CONFIG:Q} ${EMBERBSD_CROSS_BUILD_PYTHON} -E -S ${EMBERBSD_TDB_QUERY} --check ${WRKDIR} ${CROSS_DESTDIR} ${TOOLDIR}/bin/${MACHINE_GNU_PLATFORM}-readelf ${MACHINE_ARCH:S/x86_64/amd64/:Q}
	${RUN}${RM} -f ${WRKDIR}/.tdb-query-failure
post-configure: emberbsd-tdb-query-result
.PHONY: emberbsd-tdb-query-result
emberbsd-tdb-query-result:
	${RUN}${TEST} ! -e ${WRKDIR}/.tdb-query-failure || { ${CAT} ${WRKDIR}/.tdb-query-failure; exit 1; }
.endif

.include "../../devel/gettext-lib/buildlink3.mk"
.include "../../lang/python/application.mk"
.include "../../lang/python/extension.mk"
.include "../../mk/pthread.buildlink3.mk"
.include "../../converters/libiconv/buildlink3.mk"
.include "../../mk/bsd.pkg.mk"
