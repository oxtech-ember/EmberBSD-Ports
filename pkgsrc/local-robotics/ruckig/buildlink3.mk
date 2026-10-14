# SPDX-License-Identifier: MIT
# Origin: EmberBSD, AI-assisted Ruckig dependency contract.
BUILDLINK_TREE+=	ruckig

.if !defined(RUCKIG_BUILDLINK3_MK)
RUCKIG_BUILDLINK3_MK:=

BUILDLINK_API_DEPENDS.ruckig+=	ruckig>=0.19.4
# Upstream ships an unversioned library and does not promise cross-release ABI.
BUILDLINK_ABI_DEPENDS.ruckig+=	ruckig-0.19.4{,nb*}
BUILDLINK_PKGSRCDIR.ruckig?=	../../local-robotics/ruckig

USE_CXX_FEATURES+=	c++20
GCC_REQD+=		16.2

.endif # RUCKIG_BUILDLINK3_MK

BUILDLINK_TREE+=	-ruckig
