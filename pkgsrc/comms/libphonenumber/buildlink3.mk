# $NetBSD$

BUILDLINK_TREE+=	libphonenumber

.if !defined(LIBPHONENUMBER_BUILDLINK3_MK)
LIBPHONENUMBER_BUILDLINK3_MK:=

BUILDLINK_API_DEPENDS.libphonenumber+=	libphonenumber>=8.13.55
BUILDLINK_PKGSRCDIR.libphonenumber?=	../../comms/libphonenumber

# The library is built with std::mutex. Public headers require the same
# macro on platforms other than Linux, macOS, and Windows.
BUILDLINK_CPPFLAGS.libphonenumber+=	-DI18N_PHONENUMBERS_USE_STDMUTEX

.include "../../devel/protobuf/buildlink3.mk"
.include "../../textproc/icu/buildlink3.mk"
.endif	# LIBPHONENUMBER_BUILDLINK3_MK

BUILDLINK_TREE+=	-libphonenumber
