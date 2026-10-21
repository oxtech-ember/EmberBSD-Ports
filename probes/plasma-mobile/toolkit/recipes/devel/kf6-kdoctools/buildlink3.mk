# $NetBSD: buildlink3.mk,v 1.11 2026/09/02 19:01:30 wiz Exp $

BUILDLINK_TREE+=	kf6-kdoctools

.if !defined(KF6_KDOCTOOLS_BUILDLINK3_MK)
KF6_KDOCTOOLS_BUILDLINK3_MK:=

BUILDLINK_API_DEPENDS.kf6-kdoctools+=	kf6-kdoctools>=6.31.0
BUILDLINK_ABI_DEPENDS.kf6-kdoctools+=	kf6-kdoctools>=6.31.0nb2
.include "../../devel/kf6-kdoctools/cross-tools.mk"

BUILDLINK_PKGSRCDIR.kf6-kdoctools?=	../../devel/kf6-kdoctools

BUILDLINK_FILES.kf6-kdoctools+=		share/kf6/kdoctools/customization/*.xsl
BUILDLINK_FILES.kf6-kdoctools+=		bin/checkXML6
BUILDLINK_FILES.kf6-kdoctools+=		bin/meinproc6

.if ${USE_CROSS_COMPILE:Uno:tl} == "yes"
# Relocatable stylesheets load customization data and DocBook XSL through
# relative paths below the buildlink prefix. Keep the default filter terms.
BUILDLINK_CONTENTS_FILTER.kf6-kdoctools?=	\
	${EGREP} '(include.*/|\.h$$|\.idl$$|\.pc$$|/lib[^/]*\.[^/]*$$|lib/cmake/|share/cmake/|^share/kf6/kdoctools/customization/)'
BUILDLINK_DEPMETHOD.docbook-xsl?=	build
.include "../../textproc/docbook-xsl/buildlink3.mk"
.endif

.include "../../textproc/libxslt/buildlink3.mk"
.include "../../textproc/libxml2/buildlink3.mk"
.include "../../x11/qt6-qtbase/buildlink3.mk"
.endif	# KF6_KDOCTOOLS_BUILDLINK3_MK

BUILDLINK_TREE+=	-kf6-kdoctools
