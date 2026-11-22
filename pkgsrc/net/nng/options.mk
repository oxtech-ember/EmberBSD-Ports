# $NetBSD: options.mk,v 1.3 2024/08/25 06:19:07 wiz Exp $

PKG_OPTIONS_VAR= PKG_OPTIONS.nng
PKG_SUPPORTED_OPTIONS= doc static
PKG_SUGGESTED_OPTIONS+= doc

.include "../../mk/bsd.options.mk"

PLIST_VARS+= doc shared static

# The release workflow publishes the rendered v2.1 reference in gh-pages.
.if !empty(PKG_OPTIONS:Mdoc)
NNG_DOCS_REV= 8935ae95671151abc53e4ae81e330789b639781c
NNG_DOCS_DISTFILE= nng-docs-${NNG_DOCS_REV}.tar.gz
DISTFILES= ${DEFAULT_DISTFILES} ${NNG_DOCS_DISTFILE}
SITES.${NNG_DOCS_DISTFILE}= -https://codeload.github.com/nanomsg/nng/tar.gz/${NNG_DOCS_REV}
EXTRACT_ONLY= ${DEFAULT_DISTFILES}
TOOL_DEPENDS+= lowdown>=3.2.1:../../textproc/lowdown
.include "../../lang/python/tool.mk"
USE_TOOLS+= bsdtar pax
INSTALLATION_DIRS+= share/doc/nng
PLIST.doc= yes

post-extract:
	${TOOLS_PATH.bsdtar} -xzf ${_DISTDIR:Q}/${NNG_DOCS_DISTFILE} -C ${WRKDIR:Q} nng-${NNG_DOCS_REV}/ref/v2.1
.endif

.if !empty(PKG_OPTIONS:Mstatic)
CMAKE_CONFIGURE_ARGS+= -DBUILD_SHARED_LIBS:BOOL=OFF
PLIST.static= yes
.else
CMAKE_CONFIGURE_ARGS+= -DBUILD_SHARED_LIBS:BOOL=ON
PLIST.shared= yes
.endif
