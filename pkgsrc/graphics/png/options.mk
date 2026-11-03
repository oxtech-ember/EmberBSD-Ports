# $NetBSD: options.mk,v 1.6 2026/08/03 13:12:26 wiz Exp $

PKG_OPTIONS_VAR=	PKG_OPTIONS.png
PKG_SUPPORTED_OPTIONS=	apng tests
PKG_SUGGESTED_OPTIONS=	# do not suggest apng without consulting tech-pkg@

.include "../../mk/bsd.options.mk"

.if !empty(PKG_OPTIONS:Mapng) || make(distinfo) || make(mdi)
APNGPATCHVERSION=		1.6.59
APNGPATCH=			libpng-${APNGPATCHVERSION}-apng.patch.gz
PATCHFILES+=			${APNGPATCH}
SITES.${APNGPATCH}=		${MASTER_SITE_SOURCEFORGE:=libpng-apng/libpng16/${APNGPATCHVERSION}/}
.endif

.if !empty(PKG_OPTIONS:Mtests)
CONFIGURE_ARGS+= --enable-tests
TEST_TARGET= check
.else
CONFIGURE_ARGS+= --disable-tests
do-test:
	@${FAIL_MSG} "Enable the tests package option before running tests."
	@${FALSE}
.endif
