# SPDX-License-Identifier: BSD-2-Clause
BUILDLINK_TREE+=	boost-headers

.if !defined(BOOST_HEADERS_BUILDLINK3_MK)
BOOST_HEADERS_BUILDLINK3_MK:=
BUILDLINK_API_DEPENDS.boost-headers+=	boost-headers>=1.92.0
BUILDLINK_ABI_DEPENDS.boost-headers+=	boost-headers-1.92.0{,nb*}
BUILDLINK_PKGSRCDIR.boost-headers?=	../../local-robotics/boost-headers
USE_CXX_FEATURES+=	c++17
GCC_REQD+=		16.2
.endif

BUILDLINK_TREE+=	-boost-headers
