# SPDX-License-Identifier: BSD-2-Clause
BUILDLINK_TREE+=	eigen3

.if !defined(EIGEN3_BUILDLINK3_MK)
EIGEN3_BUILDLINK3_MK:=
BUILDLINK_API_DEPENDS.eigen3+=	eigen3>=5.0.1
BUILDLINK_ABI_DEPENDS.eigen3+=	eigen3-5.0.1{,nb*}
BUILDLINK_PKGSRCDIR.eigen3?=	../../local-robotics/eigen3
BUILDLINK_DEPMETHOD.eigen3?=	build
USE_CXX_FEATURES+=		c++17
GCC_REQD+=			16.2
.endif

BUILDLINK_TREE+=	-eigen3
