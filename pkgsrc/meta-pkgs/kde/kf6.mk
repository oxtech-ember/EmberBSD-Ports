# $NetBSD: kf6.mk,v 1.12 2026/09/06 10:05:11 markd Exp $
# used by archivers/kf6-karchive/Makefile
# used by devel/kf6-kbookmarks/Makefile
# used by devel/kf6-kcmutils/Makefile
# used by devel/kf6-kcolorscheme/Makefile
# used by devel/kf6-kconfig/Makefile
# used by devel/kf6-kcoreaddons/Makefile
# used by devel/kf6-kcrash/Makefile
# used by devel/kf6-kdeclarative/Makefile
# used by devel/kf6-kdoctools/Makefile
# used by devel/kf6-ki18n/Makefile
# used by devel/kf6-kidletime/Makefile
# used by devel/kf6-kio/Makefile
# used by devel/kf6-kitemmodels/Makefile
# used by devel/kf6-knotifications/Makefile
# used by devel/kf6-knotifyconfig/Makefile
# used by devel/kf6-kpackage/Makefile
# used by devel/kf6-kparts/Makefile
# used by devel/kf6-kpeople/Makefile
# used by devel/kf6-kpty/Makefile
# used by devel/kf6-krunner/Makefile
# used by devel/kf6-kservice/Makefile
# used by devel/kf6-ktexteditor/Makefile
# used by devel/kf6-purpose/Makefile
# used by devel/kf6-threadweaver/Makefile
# used by graphics/breeze-icons/Makefile
# used by graphics/kf6-kiconthemes/Makefile
# used by graphics/kf6-kimageformats/Makefile
# used by graphics/kf6-kplotting/Makefile
# used by graphics/kf6-ksvg/Makefile
# used by graphics/kf6-prison/Makefile
# used by mail/kf6-kmime/Makefile
# used by misc/kf6-attica/Makefile
# used by misc/kf6-kcontacts/Makefile
# used by misc/kf6-kdav/Makefile
# used by misc/kf6-kquickcharts/Makefile
# used by misc/kf6-kstatusnotifieritem/Makefile
# used by misc/kf6-kunitconversion/Makefile
# used by misc/kf6-kuserfeedback/Makefile
# used by net/kf6-kdnssd/Makefile
# used by net/kf6-knewstuff/Makefile
# used by security/kf6-kauth/Makefile
# used by security/kf6-kdesu/Makefile
# used by security/kf6-kwallet/Makefile
# used by sysutils/kf6-baloo/Makefile
# used by sysutils/kf6-kdbusaddons/Makefile
# used by sysutils/kf6-kfilemetadata/Makefile
# used by sysutils/kf6-solid/Makefile
# used by textproc/kf6-kcodecs/Makefile
# used by textproc/kf6-kcompletion/Makefile
# used by textproc/kf6-ktexttemplate/Makefile
# used by textproc/kf6-sonnet/Makefile
# used by textproc/kf6-syntax-highlighting/Makefile
# used by time/kf6-kcalendarcore/Makefile
# used by time/kf6-kholidays/Makefile
# used by www/kf6-syndication/Makefile
# used by x11/kf6-frameworkintegration/Makefile
# used by x11/kf6-kconfigwidgets/Makefile
# used by x11/kf6-kded/Makefile
# used by x11/kf6-kglobalaccel/Makefile
# used by x11/kf6-kguiaddons/Makefile
# used by x11/kf6-kirigami/Makefile
# used by x11/kf6-kitemviews/Makefile
# used by x11/kf6-kjobwidgets/Makefile
# used by x11/kf6-ktextwidgets/Makefile
# used by x11/kf6-kwidgetsaddons/Makefile
# used by x11/kf6-kwindowsystem/Makefile
# used by x11/kf6-kxmlgui/Makefile
# used by x11/kf6-qqc2-desktop-style/Makefile

KF6VER=		6.31.0

.include "../../mk/bsd.prefs.mk"

# EmberBSD: only the recipes prepared together in this toolkit export.
_EMBERBSD_KF6VER_RECIPES= \
    archivers/kf6-karchive \
    devel/kf6-kbookmarks \
    devel/kf6-kcmutils \
    devel/kf6-kcolorscheme \
    devel/kf6-kconfig \
    devel/kf6-kcoreaddons \
    devel/kf6-kcrash \
    devel/kf6-kdeclarative \
    devel/kf6-kdoctools \
    devel/kf6-ki18n \
    devel/kf6-kidletime \
    devel/kf6-kio \
    devel/kf6-kitemmodels \
    devel/kf6-knotifications \
    devel/kf6-knotifyconfig \
    devel/kf6-kpackage \
    devel/kf6-kparts \
    devel/kf6-kpeople \
    devel/kf6-kpty \
    devel/kf6-krunner \
    devel/kf6-kservice \
    devel/kf6-ktexteditor \
    devel/kf6-purpose \
    devel/kf6-threadweaver \
    graphics/breeze-icons \
    graphics/kf6-kiconthemes \
    graphics/kf6-kimageformats \
    graphics/kf6-kplotting \
    graphics/kf6-ksvg \
    graphics/kf6-prison \
    mail/kf6-kmime \
    misc/kf6-attica \
    misc/kf6-kcontacts \
    misc/kf6-kdav \
    misc/kf6-kquickcharts \
    misc/kf6-kstatusnotifieritem \
    misc/kf6-kunitconversion \
    misc/kf6-kuserfeedback \
    net/kf6-kdnssd \
    net/kf6-knewstuff \
    security/kf6-kauth \
    security/kf6-kdesu \
    security/kf6-kwallet \
    sysutils/kf6-baloo \
    sysutils/kf6-kdbusaddons \
    sysutils/kf6-kfilemetadata \
    sysutils/kf6-solid \
    textproc/kf6-kcodecs \
    textproc/kf6-kcompletion \
    textproc/kf6-ktexttemplate \
    textproc/kf6-sonnet \
    textproc/kf6-syntax-highlighting \
    time/kf6-kcalendarcore \
    time/kf6-kholidays \
    www/kf6-syndication \
    x11/kf6-frameworkintegration \
    x11/kf6-kconfigwidgets \
    x11/kf6-kded \
    x11/kf6-kglobalaccel \
    x11/kf6-kguiaddons \
    x11/kf6-kirigami \
    x11/kf6-kitemviews \
    x11/kf6-kjobwidgets \
    x11/kf6-ktextwidgets \
    x11/kf6-kwidgetsaddons \
    x11/kf6-kwindowsystem \
    x11/kf6-kxmlgui \
    x11/kf6-qqc2-desktop-style
.if empty(_EMBERBSD_KF6VER_RECIPES:M${PKGPATH})
PKG_FAIL_REASON+= "Frameworks 6 recipe ${PKGPATH} is not prepared in the Plasma toolkit"
.endif
.if ${KF6VER} != "6.31.0"
PKG_FAIL_REASON+= "The common toolkit requires KF6VER=6.31.0"
.endif

CATEGORIES+=	kde
MASTER_SITES=	${MASTER_SITE_KDE:=frameworks/${KF6VER:R}/}
EXTRACT_SUFX=	.tar.xz
PKGNAME?=	kf6-${DISTNAME}

BUILDLINK_API_DEPENDS.extra-cmake-modules+=	extra-cmake-modules>=${KF6VER}
.include "../../devel/extra-cmake-modules/buildlink3.mk"
TOOLS_DEPENDS.cmake= cmake>=3.0:../../devel/cmake

CMAKE_CONFIGURE_ARGS+=	-DKF_IGNORE_PLATFORM_CHECK=true

# ECM queries native qtpaths during a cross build. Those host installation
# directories are not destinations in the target package.
.if ${USE_CROSS_COMPILE:Uno:tl} == "yes"
# Application templates are data; ECM otherwise omits them during cross builds.
CMAKE_CONFIGURE_ARGS+= -DKDE_INSTALL_APP_TEMPLATES=ON
# Imported pkg-config targets require real target include/library directories.
CONFIGURE_ENV+= PKG_CONFIG_SYSROOT_DIR=${CROSS_DESTDIR:Q}
CMAKE_CONFIGURE_ARGS+= -DKDE_INSTALL_QTPLUGINDIR=qt6/plugins
CMAKE_CONFIGURE_ARGS+= -DKDE_INSTALL_QMLDIR=qt6/qml
CMAKE_CONFIGURE_ARGS+= -DKDE_INSTALL_QTMETATYPESDIR=qt6/metatypes
CMAKE_CONFIGURE_ARGS+= -DKDE_INSTALL_QTQCHDIR=qt6/doc
.endif

USE_CXX_FEATURES+=	c++20

.include "../../meta-pkgs/kde/Makefile.common"
