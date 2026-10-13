# $NetBSD: Makefile,v 1.73 2026/09/06 11:02:44 markd Exp $

DISTNAME=	kio-extras-${KAPPSVER}
CATEGORIES=	misc

HOMEPAGE=	https://kde.org/applications/internet/
COMMENT=	Additional components to increase the functionality of KIO
LICENSE=	gnu-gpl-v2

.include "../../meta-pkgs/kde/applications.mk"

# Cross builds use the shared native KDocTools host tooling
# (toolkit/cross/doctools.md). The SMB, MTP, NFS, AFC workers and the
# EXR/audio/appimage thumbnail creators are not built: samba4, libmtp,
# tirpc, libimobiledevice, openexr, taglib and libappimage are not ported
# to the common stack. Upstream CMake skips these workers gracefully.


# kde-info2html runs on the target with the NetBSD base perl; the pkgsrc
# REPLACE_PERL/host-tool mechanism must not rewrite its interpreter.
USE_TOOLS+=	msgmerge pkg-config

# kde-info2html runs on the target with the NetBSD base perl.
CHECK_INTERPRETER_SKIP+=	share/kio_info/kde-info2html*

# libutempter is not ported; the fish worker builds without utmp records.
CMAKE_CONFIGURE_ARGS+=	-DCMAKE_DISABLE_FIND_PACKAGE_UTEMPTER:BOOL=TRUE


SUBST_CLASSES+=		paths
SUBST_FILES.paths=	info/kde-info2html.conf
SUBST_VARS.paths=	LOCALBASE
SUBST_STAGE.paths=	pre-configure

SUBST_CLASSES+=		fix-moc
SUBST_STAGE.fix-moc=	post-configure
SUBST_MESSAGE.fix-moc=	Cleaning up MOC includes
SUBST_FILES.fix-moc=	_KDE_build/*/CMakeFiles/*_autogen.dir/AutogenInfo.json
SUBST_NOOP_OK.fix-moc=	yes
SUBST_SED.fix-moc=	-e 's;"${PREFIX}/include",;;g'

BUILDLINK_TRANSFORM.SunOS+=	rm:-Wl,--as-needed

.include "../../mk/bsd.prefs.mk"

.if ${OPSYS} == "SunOS"
TOOLS_CREATE+=		md5sum
TOOLS_PATH.md5sum=	${PREFIX}/bin/gmd5sum
.endif

.include "../../archivers/kf6-karchive/buildlink3.mk"
.include "../../databases/shared-mime-info/buildlink3.mk"
.include "../../devel/gperf/buildlink3.mk"
.include "../../devel/kf6-kcmutils/buildlink3.mk"
.include "../../devel/kf6-kcoreaddons/buildlink3.mk"
.include "../../devel/kf6-ki18n/buildlink3.mk"
.include "../../devel/kf6-kio/buildlink3.mk"
.include "../../devel/kf6-kpty/buildlink3.mk"
.include "../../devel/qcoro/buildlink3.mk"
.include "../../devel/qt6-qt5compat/buildlink3.mk"
.include "../../graphics/exiv2/buildlink3.mk"
.include "../../graphics/libkexiv2/buildlink3.mk"
.include "../../graphics/qt6-qtsvg/buildlink3.mk"
.include "../../multimedia/phonon-qt6/buildlink3.mk"
.include "../../net/kf6-kdnssd/buildlink3.mk"
.include "../../security/libssh/buildlink3.mk"
.include "../../textproc/kf6-syntax-highlighting/buildlink3.mk"
.include "../../x11/kf6-kguiaddons/buildlink3.mk"
.include "../../x11/plasma6-plasma-activities/buildlink3.mk"
.include "../../x11/plasma6-plasma-activities-stats/buildlink3.mk"
.include "../../x11/qt6-qtbase/buildlink3.mk"
.include "../../mk/bsd.pkg.mk"
