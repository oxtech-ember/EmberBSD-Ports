# STATUS: does not complete yet; see the shared-executor failure marker
# note in net/samba4. The cross-execute wiring mirrors databases/tdb.

# $NetBSD: Makefile,v 1.53 2026/08/10 16:45:32 adam Exp $

DISTNAME=	talloc-2.5.0
CATEGORIES=	devel
MASTER_SITES=	https://www.samba.org/ftp/talloc/

MAINTAINER=	pkgsrc-users@NetBSD.org
HOMEPAGE=	https://talloc.samba.org/talloc/doc/html/index.html
COMMENT=	Hierarchical pool based memory allocator with destructors
LICENSE=	gnu-gpl-v3 AND gnu-lgpl-v3

TOOL_DEPENDS+=	libxslt-[0-9]*:../../textproc/libxslt
TOOL_DEPENDS+=	docbook-xsl-[0-9]*:../../textproc/docbook-xsl

# include/talloc.h
CONFLICTS+=	samba<=4.6.8nb3

USE_TOOLS+=		pkg-config
HAS_CONFIGURE=		yes
CONFIGURE_ARGS+=	--mandir=${PREFIX}/${PKGMANDIR}
CONFIGURE_ARGS+=	--abi-check-disable
CONFIGURE_ARGS+=	--disable-symbol-versions
.if defined(MAKE_JOBS) && !empty(MAKE_JOBS) && !(defined(MAKE_JOBS_SAFE) && ${MAKE_JOBS_SAFE:U:tl} == no)
CONFIGURE_ARGS+=	--jobs=${MAKE_JOBS}
.else
CONFIGURE_ARGS+=	--jobs=1
.endif
PKGCONFIG_OVERRIDE+=	talloc.pc.in
PKGCONFIG_OVERRIDE+=	pytalloc-util.pc.in
TEST_TARGET=		test

PY_PATCHPLIST=		yes
REPLACE_TOOL_PYTHON+=	buildtools/bin/waf
MAKE_FLAGS+=		WAF_BINARY=${TOOL_PYTHONBIN}\ ${WRKSRC}/buildtools/bin/waf

SUBST_CLASSES+=		docbook
SUBST_MESSAGE.docbook=	Fixing docbook URLs.
SUBST_FILES.docbook+=	buildtools/wafsamba/samba_conftests.py
SUBST_FILES.docbook+=	buildtools/wafsamba/wafsamba.py
SUBST_STAGE.docbook=	pre-configure
SUBST_SED.docbook+=	-e 's,http://docbook.sourceforge.net/release/xsl/current,${PREFIX}/share/xsl/docbook,g'


.include "../../mk/bsd.prefs.mk"
.if ${USE_CROSS_COMPILE:Uno:tl} == "yes"
# Waf runs on the host; its compiled feature probes run on the EmberBSD
# target through the shared executor (same flow as databases/tdb).
# Fetch, checksum and extract do not use these build-host inputs, so they
# are checked when configure starts instead of refusing the whole package.
_EMBER_TALLOC_INPUT_ERRORS=
.for _input in EMBERBSD_CROSS_BUILD_PYTHON EMBERBSD_GI_QUERY_CONFIG
.if empty(${_input}:M/*) || !empty(${_input}:C/[A-Za-z0-9_.\/-]//g) || !exists(${${_input}})
_EMBER_TALLOC_INPUT_ERRORS+= ${_input}
.endif
.endfor
.if empty(EMBERBSD_SDK_SOURCE:M/*) || !empty(EMBERBSD_SDK_SOURCE:C/[A-Za-z0-9_.\/-]//g) || !exists(${EMBERBSD_SDK_SOURCE}/src/emberbsd_sdk/__init__.py)
_EMBER_TALLOC_INPUT_ERRORS+= EMBERBSD_SDK_SOURCE
.endif
pre-configure: emberbsd-talloc-inputs
.PHONY: emberbsd-talloc-inputs
emberbsd-talloc-inputs:
.for _input in ${_EMBER_TALLOC_INPUT_ERRORS}
.if ${_input} == "EMBERBSD_SDK_SOURCE"
	@${ERROR_MSG} "EMBERBSD_SDK_SOURCE must name an absolute SDK source directory without shell metacharacters"
.else
	@${ERROR_MSG} "${_input} must name an existing absolute file without shell metacharacters"
.endif
.endfor
.if !empty(_EMBER_TALLOC_INPUT_ERRORS)
	@${FALSE}
.endif
EMBERBSD_TALLOC_QUERY= ${.CURDIR}/../../devel/gobject-introspection/files/target-query.py
EMBERBSD_TALLOC_EXECUTOR= ${EMBERBSD_CROSS_BUILD_PYTHON} -E -S ${EMBERBSD_TALLOC_QUERY} --execute
CONFIGURE_ARGS+= --cross-compile --cross-execute=${EMBERBSD_TALLOC_EXECUTOR:Q}
# Parallel configure mutates provider files while a query walks them.
CONFIGURE_ARGS+= --jobs=1
# The Python binding probes build host binaries that the shared target
# executor rightly refuses; the KIO SMB consumer needs the C library only.
CONFIGURE_ARGS+= --disable-python
CONFIGURE_ENV+= EMBERBSD_SDK_SOURCE=${EMBERBSD_SDK_SOURCE:Q}
CONFIGURE_ENV+= EMBERBSD_GI_TARGET=${MACHINE_ARCH:S/x86_64/amd64/}
CONFIGURE_ENV+= EMBERBSD_GI_QUERY_CONFIG=${EMBERBSD_GI_QUERY_CONFIG:Q}
CONFIGURE_ENV+= EMBERBSD_GI_FAILURE_MARKER=${WRKDIR}/.talloc-query-failure
CONFIGURE_ENV+= PYTHON=${TOOL_PYTHONBIN:Q}
CONFIGURE_ENV+= PYTHONPATH=${WRKDIR}/.pysite:${CROSS_DESTDIR}${LOCALBASE}/${PYLIB}
CONFIGURE_ENV+= PYTHON_CONFIG=${TOOL_PYTHONBIN:Q}\ ${CROSS_DESTDIR}${PYTHONBIN}-config
pre-configure: emberbsd-talloc-query
.PHONY: emberbsd-talloc-query
emberbsd-talloc-query: emberbsd-talloc-inputs
	${RUN}${SETENV} EMBERBSD_SDK_SOURCE=${EMBERBSD_SDK_SOURCE:Q} EMBERBSD_GI_TARGET=${MACHINE_ARCH:S/x86_64/amd64/:Q} EMBERBSD_GI_QUERY_CONFIG=${EMBERBSD_GI_QUERY_CONFIG:Q} ${EMBERBSD_CROSS_BUILD_PYTHON} -E -S ${EMBERBSD_TALLOC_QUERY} --check ${WRKDIR} ${CROSS_DESTDIR} ${TOOLDIR}/bin/${MACHINE_ARCH}--netbsd-readelf ${MACHINE_ARCH:S/x86_64/amd64/:Q}
	${RUN}${RM} -f ${WRKDIR}/.talloc-query-failure
post-configure: emberbsd-talloc-query-result
.PHONY: emberbsd-talloc-query-result
emberbsd-talloc-query-result:
	${RUN}${TEST} ! -e ${WRKDIR}/.talloc-query-failure || { ${CAT} ${WRKDIR}/.talloc-query-failure; exit 1; }
.endif

.include "../../devel/gettext-lib/buildlink3.mk"
.include "../../lang/python/application.mk"
.include "../../lang/python/extension.mk"
.include "../../mk/dlopen.buildlink3.mk"
.include "../../mk/pthread.buildlink3.mk"
.include "../../mk/bsd.pkg.mk"
