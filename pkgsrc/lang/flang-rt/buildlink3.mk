# $NetBSD$

BUILDLINK_TREE+=	flang-rt

.if !defined(FLANG_RT_BUILDLINK3_MK)
FLANG_RT_BUILDLINK3_MK:=

BUILDLINK_API_DEPENDS.flang-rt+=	flang-rt>=23.1.4nb2
BUILDLINK_PKGSRCDIR.flang-rt?=		../../lang/flang-rt
# The modules and headers are read through the Flang resource directory; only
# the runtime library is linked through buildlink.
BUILDLINK_FILES.flang-rt=		lib/libflang_rt.runtime.*
.endif	# FLANG_RT_BUILDLINK3_MK

BUILDLINK_TREE+=	-flang-rt
