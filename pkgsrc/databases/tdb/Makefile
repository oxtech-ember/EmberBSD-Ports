# $NetBSD: Makefile,v 1.60 2026/01/22 21:00:42 adam Exp $

DISTNAME=	tdb-1.4.15
PKGREVISION=	8
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

PKG_OPTIONS_VAR=	PKG_OPTIONS.tdb
PKG_SUPPORTED_OPTIONS=	python
PKG_SUGGESTED_OPTIONS=	python
.include "../../mk/bsd.options.mk"

PLIST_VARS+=	python
.if !empty(PKG_OPTIONS:Mpython)
PLIST.python=	yes
PY_PATCHPLIST=		yes
.else
PYTHON_FOR_BUILD_ONLY=	tool
CONFIGURE_ARGS+=	--disable-python
.endif
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
# Waf runs on the host. Its compiled feature probes are answered from the
# stored per-platform answers in files/cross-answers (devel/talloc/waf-cross.mk).
.include "../../devel/talloc/waf-cross.mk"
# Reuse pkgsrc's target sysconfig environment during configure as well as make.
# Execute the target python-config script with the host interpreter.
.if !empty(PKG_OPTIONS:Mpython)
CONFIGURE_ENV+= PYTHONPATH=${WRKDIR}/.pysite:${CROSS_DESTDIR}${LOCALBASE}/${PYLIB}
CONFIGURE_ENV+= PYTHON_CONFIG=${TOOL_PYTHONBIN:Q}\ ${CROSS_DESTDIR}${PYTHONBIN}-config
.endif
.endif

.include "../../devel/gettext-lib/buildlink3.mk"
.include "../../lang/python/application.mk"
.if !empty(PKG_OPTIONS:Mpython)
.include "../../lang/python/extension.mk"
.endif
.include "../../mk/pthread.buildlink3.mk"
.include "../../converters/libiconv/buildlink3.mk"
.include "../../mk/bsd.pkg.mk"
