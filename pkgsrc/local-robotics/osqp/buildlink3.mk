# SPDX-License-Identifier: MIT
# Origin: EmberBSD, AI-assisted native OSQP consumer metadata.
BUILDLINK_TREE+=	osqp

.if !defined(OSQP_BUILDLINK3_MK)
OSQP_BUILDLINK3_MK:=

BUILDLINK_API_DEPENDS.osqp+=	osqp>=1.0.0
BUILDLINK_ABI_DEPENDS.osqp+=	osqp-1.0.0{,nb*}
BUILDLINK_PKGSRCDIR.osqp?=	../../local-robotics/osqp
BUILDLINK_INCDIRS.osqp+=		include/osqp
.endif

BUILDLINK_TREE+=	-osqp
