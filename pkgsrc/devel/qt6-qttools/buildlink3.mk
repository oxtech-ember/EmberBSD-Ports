# $NetBSD: buildlink3.mk,v 1.23 2026/09/02 19:01:43 wiz Exp $

BUILDLINK_TREE+=	qt6-qttools

.if !defined(QT6_QTTOOLS_BUILDLINK3_MK)
QT6_QTTOOLS_BUILDLINK3_MK:=

BUILDLINK_API_DEPENDS.qt6-qttools+=	qt6-qttools>=6.12.0
BUILDLINK_ABI_DEPENDS.qt6-qttools+=	qt6-qttools>=6.12.0
BUILDLINK_PKGSRCDIR.qt6-qttools?=	../../devel/qt6-qttools

BUILDLINK_FILES.qt6-qttools+=		qt6/bin/lconvert
BUILDLINK_FILES.qt6-qttools+=		qt6/bin/lrelease
BUILDLINK_FILES.qt6-qttools+=		qt6/bin/lupdate
BUILDLINK_FILES.qt6-qttools+=		qt6/libexec/lprodump
BUILDLINK_FILES.qt6-qttools+=		qt6/libexec/lrelease-pro
BUILDLINK_FILES.qt6-qttools+=		qt6/libexec/lupdate-pro

pkgbase := qt6-qttools
.include "../../mk/pkg-build-options.mk"

# The host-tools build has only the Linguist tools and qtattributionsscanner
# and does not use QtDeclarative (see options.mk and the Makefile).
.if !${PKG_BUILD_OPTIONS.qt6-qttools:Mhost-tools}
.include "../../lang/qt6-qtdeclarative/buildlink3.mk"
.endif
.include "../../x11/qt6-qtbase/buildlink3.mk"
.endif	# QT6_QTTOOLS_BUILDLINK3_MK

BUILDLINK_TREE+=	-qt6-qttools
