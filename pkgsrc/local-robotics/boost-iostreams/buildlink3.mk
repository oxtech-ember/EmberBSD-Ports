# SPDX-License-Identifier: BSD-2-Clause
BUILDLINK_TREE+=	boost-iostreams

.if !defined(BOOST_IOSTREAMS_BUILDLINK3_MK)
BOOST_IOSTREAMS_BUILDLINK3_MK:=
BUILDLINK_API_DEPENDS.boost-iostreams+=	boost-iostreams>=1.92.0
BUILDLINK_ABI_DEPENDS.boost-iostreams+=	boost-iostreams-1.92.0{,nb*}
BUILDLINK_PKGSRCDIR.boost-iostreams?=	../../local-robotics/boost-iostreams
USE_CXX_FEATURES+=	c++17
GCC_REQD+=	16.2
.include "../../local-robotics/boost-headers/buildlink3.mk"
.include "../../devel/zlib/buildlink3.mk"
.include "../../archivers/bzip2/buildlink3.mk"
.include "../../archivers/xz/buildlink3.mk"
.endif

BUILDLINK_TREE+=	-boost-iostreams
