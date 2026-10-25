# $NetBSD$
BUILDLINK_TREE+= libiio
.if !defined(LIBIIO_BUILDLINK3_MK)
LIBIIO_BUILDLINK3_MK:=
BUILDLINK_API_DEPENDS.libiio+= libiio>=1.0.0
BUILDLINK_PKGSRCDIR.libiio?= ../../devel/libiio
.include "../../devel/libusb1/buildlink3.mk"
.include "../../textproc/libxml2/buildlink3.mk"
.include "../../archivers/zstd/buildlink3.mk"
.endif
BUILDLINK_TREE+= -libiio
