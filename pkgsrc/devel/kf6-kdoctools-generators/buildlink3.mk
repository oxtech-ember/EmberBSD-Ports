# $NetBSD$
# Origin: EmberBSD (AI-assisted). Native consumers of devel/kf6-kdoctools link
# the library, generators, DocBook data and CMake files from this package.

BUILDLINK_TREE+=	kf6-kdoctools-generators

.if !defined(KF6_KDOCTOOLS_GENERATORS_BUILDLINK3_MK)
KF6_KDOCTOOLS_GENERATORS_BUILDLINK3_MK:=

BUILDLINK_API_DEPENDS.kf6-kdoctools-generators+=	kf6-kdoctools-generators>=6.32.0nb2
BUILDLINK_PKGSRCDIR.kf6-kdoctools-generators?=	../../devel/kf6-kdoctools-generators

BUILDLINK_FILES.kf6-kdoctools-generators+=	share/kf6/kdoctools/customization/*.xsl
BUILDLINK_FILES.kf6-kdoctools-generators+=	bin/checkXML6
BUILDLINK_FILES.kf6-kdoctools-generators+=	bin/meinproc6

.include "../../textproc/libxslt/buildlink3.mk"
.include "../../textproc/libxml2/buildlink3.mk"
.include "../../x11/qt6-qtbase/buildlink3.mk"
.endif	# KF6_KDOCTOOLS_GENERATORS_BUILDLINK3_MK

BUILDLINK_TREE+=	-kf6-kdoctools-generators
