# $NetBSD: options.mk,v 1.3 2024/08/25 06:19:07 wiz Exp $
# The formatter runs on the build host in native and cross builds.

PKG_OPTIONS_VAR= PKG_OPTIONS.nng
PKG_SUPPORTED_OPTIONS= doc static
PKG_SUGGESTED_OPTIONS+= doc

.include "../../mk/bsd.options.mk"

PLIST_VARS+= doc shared static

.if !empty(PKG_OPTIONS:Mdoc)
CMAKE_CONFIGURE_ARGS+= -DNNG_ENABLE_DOC:BOOL=ON
PLIST.doc= yes
.  if defined(EMBERBSD_BUILD_ASCIIDOCTOR)
.    if empty(EMBERBSD_BUILD_ASCIIDOCTOR:M/*) || !exists(${EMBERBSD_BUILD_ASCIIDOCTOR})
PKG_FAIL_REASON+= "EMBERBSD_BUILD_ASCIIDOCTOR must name an existing absolute host executable"
.    else
_EMBERBSD_ASCIIDOCTOR_VERSION!= if test -x ${EMBERBSD_BUILD_ASCIIDOCTOR:Q} && \
    ember_asciidoctor_banner=$$(${EMBERBSD_BUILD_ASCIIDOCTOR:Q} --version); then \
    printf '%s\n' "$$ember_asciidoctor_banner" | \
    ${AWK} '/^Asciidoctor [0-9]/ { print $$2; exit }'; fi
_EMBERBSD_ASCIIDOCTOR_SUPPORTED!= ${PKG_ADMIN} pmatch 'asciidoctor>=2.0.26<3' \
    asciidoctor-${_EMBERBSD_ASCIIDOCTOR_VERSION:Q} && echo yes || echo no
.      if ${_EMBERBSD_ASCIIDOCTOR_SUPPORTED} != "yes"
PKG_FAIL_REASON+= "EMBERBSD_BUILD_ASCIIDOCTOR must successfully report Asciidoctor >=2.0.26 and <3"
.      endif
.    endif
CMAKE_CONFIGURE_ARGS+= -DASCIIDOCTOR:FILEPATH=${EMBERBSD_BUILD_ASCIIDOCTOR}
.  else
.include "../../lang/ruby/rubyversion.mk"
TOOL_DEPENDS+= ${RUBY_PKGPREFIX}-asciidoctor>=2.0.26<3:../../textproc/ruby-asciidoctor
CMAKE_CONFIGURE_ARGS+= -DASCIIDOCTOR:FILEPATH=${TOOLBASE}/bin/asciidoctor${RUBY_VER}
.  endif
.else
CMAKE_CONFIGURE_ARGS+= -DNNG_ENABLE_DOC:BOOL=OFF
.endif

.if !empty(PKG_OPTIONS:Mstatic)
CMAKE_CONFIGURE_ARGS+= -DBUILD_SHARED_LIBS:BOOL=OFF
PLIST.static= yes
.else
CMAKE_CONFIGURE_ARGS+= -DBUILD_SHARED_LIBS:BOOL=ON
PLIST.shared= yes
.endif
