# $NetBSD: Makefile,v 1.354 2026/09/02 19:04:05 wiz Exp $

DISTNAME=	wireshark-4.6.8
PKGREVISION=	1
CATEGORIES=	net
MASTER_SITES=	https://www.wireshark.org/download/src/
EXTRACT_SUFX=	.tar.xz

MAINTAINER=	pkgsrc-users@NetBSD.org
HOMEPAGE=	https://www.wireshark.org/
COMMENT=	Network protocol analyzer
LICENSE=	gnu-gpl-v2

CONFLICTS+=	ethereal-[0-9]*

DEPENDS+=	lemon-[0-9]*:../../devel/lemon

CMAKE_CONFIGURE_ARGS+=		-DCMAKE_BUILD_TYPE=Release
CMAKE_CONFIGURE_ARGS+=		-DENABLE_APPLICATION_BUNDLE=OFF
CMAKE_CONFIGURE_ARGS+=		-DVCSVERSION_OVERRIDE=${PKGVERSION_NOREV}

USE_LANGUAGES=		c c++
USE_TOOLS+=		gmake perl pkg-config bison lex
PKGCONFIG_OVERRIDE+=	resources/wireshark.pc.in

CHECK_PORTABILITY_SKIP+=	packaging/macosx/*/*
CHECK_PORTABILITY_SKIP+=	packaging/macosx/osx-app.sh.in
CHECK_PORTABILITY_SKIP+=	tools/bsd-setup.sh

PTHREAD_OPTS+=		require

PYTHON_FOR_BUILD_ONLY=		yes

REPLACE_PYTHON+=	tools/asn2deb
REPLACE_PYTHON+=	tools/asn2wrs.py
REPLACE_PYTHON+=	tools/html2text.py
REPLACE_PYTHON+=	tools/idl2deb
REPLACE_PYTHON+=	tools/indexcap.py
REPLACE_PYTHON+=	tools/msnchat
REPLACE_PYTHON+=	tools/ncp2222.py
REPLACE_PYTHON+=	tools/pkt-from-core.py
REPLACE_PYTHON+=	tools/rdps.py

CFLAGS.SunOS+=		-D__EXTENSIONS__ # for getc_unlocked(3)

.include "../../mk/bsd.prefs.mk"
.include "options.mk"

.if ${MACHINE_PLATFORM:MDarwin-[567].*-*}
USE_BUILTIN.libpcap=	no
.endif

# Extra post install targets are in options.mk
post-install: ${POST_INSTALL_TARGETS}

# wireshark uses gdk_pixbuf_new_from_inline which is deprecated, but asks
# to hide deprecated prototypes. This leads to pointer truncation.
# gui_utils.c:514:12: warning: incompatible integer to pointer conversion
# assigning to 'GdkPixbuf *' (aka 'struct _GdkPixbuf *') from 'int'
# [-Wint-conversion]
BUILDLINK_TRANSFORM+=	rm:-DGDK_PIXBUF_DISABLE_DEPRECATED

SUBST_CLASSES+=		lemon
SUBST_STAGE.lemon=	pre-configure
SUBST_MESSAGE.lemon=	Fixing hard-coded path to lemon/lempar.c.
SUBST_FILES.lemon=	cmake/modules/UseLemon.cmake
SUBST_SED.lemon=	-e 's,/usr/share,${PREFIX}/share,g'

.include "../../archivers/brotli/buildlink3.mk"
.include "../../archivers/lz4/buildlink3.mk"
.include "../../archivers/minizip/buildlink3.mk"
.include "../../archivers/zlib-ng/buildlink3.mk"
.include "../../archivers/zstd/buildlink3.mk"
.include "../../audio/libopus/buildlink3.mk"
.include "../../audio/opencore-amr/buildlink3.mk"
.include "../../audio/speexdsp/buildlink3.mk"
.include "../../devel/cmake/build.mk"
.include "../../devel/glib2/buildlink3.mk"
.include "../../devel/libsmi/buildlink3.mk"
.include "../../devel/pcre2/buildlink3.mk"
.include "../../devel/snappy/buildlink3.mk"
.include "../../devel/xxhash/buildlink3.mk"
.include "../../geography/libmaxminddb/buildlink3.mk"
.include "../../lang/python/application.mk"
BUILDLINK_API_DEPENDS.libcares+=	libcares>=1.13.0
.include "../../net/libcares/buildlink3.mk"
.include "../../net/libpcap/buildlink3.mk"
.include "../../security/gnutls/buildlink3.mk"
.include "../../security/libgcrypt/buildlink3.mk"
.include "../../security/libssh/buildlink3.mk"
.include "../../textproc/libxml2/buildlink3.mk"
.include "../../mk/krb5.buildlink3.mk"
.include "../../mk/pthread.buildlink3.mk"

# EmberBSD cross addition: the bundled lemon parser generator would be
# compiled for the target and cannot run on the build host. Use the
# native lemon from the host bootstrap prefix instead.
.  if ${USE_CROSS_COMPILE:U:tl} == "yes"
SUBST_CLASSES:=	${SUBST_CLASSES:Nlemon}
SUBST_CLASSES+=		emberlemon
SUBST_STAGE.emberlemon=	pre-configure
SUBST_MESSAGE.emberlemon=	Pointing UseLemon at the host lemon.
SUBST_FILES.emberlemon=	cmake/modules/UseLemon.cmake
SUBST_SED.emberlemon=	-e 's,/usr/share/lemon/lempar.c,${EMBERBSD_CROSS_HOST_PREFIX}/share/lemon/lempar.c,g' \
	-e 's,/usr/pkg/share/lemon/lempar.c,${EMBERBSD_CROSS_HOST_PREFIX}/share/lemon/lempar.c,g'
CMAKE_CONFIGURE_ARGS+=	-DLEMON_EXECUTABLE=${EMBERBSD_CROSS_HOST_PREFIX}/bin/lemon
# The libssh-based remote-capture extcaps do not pick up the GSS
# libraries of the builtin heimdal when cross-linking; keep them out
# of the board CLI kit until that link is repaired.
CMAKE_CONFIGURE_ARGS+=	-DBUILD_sshdump=OFF -DBUILD_ciscodump=OFF -DBUILD_wifidump=OFF
PLIST_VARS+=	sshdump
# Their extcap wrapper scripts still install without the binaries and
# break the cross ELF metadata check; drop them and their PLIST entries.
ember-remove-ssh-extcaps:
	${RM} -f ${DESTDIR}${PREFIX}/libexec/wireshark/extcap/sshdump \
	    ${DESTDIR}${PREFIX}/libexec/wireshark/extcap/ciscodump \
	    ${DESTDIR}${PREFIX}/libexec/wireshark/extcap/wifidump
POST_INSTALL_TARGETS+=	ember-remove-ssh-extcaps
.  else
PLIST.sshdump=	yes
.  endif

.include "../../mk/bsd.pkg.mk"
