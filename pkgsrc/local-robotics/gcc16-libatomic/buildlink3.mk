# SPDX-License-Identifier: BSD-2-Clause
BUILDLINK_TREE+=	gcc16-libatomic

.if !defined(GCC16_LIBATOMIC_BUILDLINK3_MK)
GCC16_LIBATOMIC_BUILDLINK3_MK:=
BUILDLINK_API_DEPENDS.gcc16-libatomic+=	gcc16-libatomic>=16.2.0
BUILDLINK_ABI_DEPENDS.gcc16-libatomic+=	gcc16-libatomic-16.2.0{,nb*}
BUILDLINK_PKGSRCDIR.gcc16-libatomic?=	../../local-robotics/gcc16-libatomic
BUILDLINK_LIBDIRS.gcc16-libatomic=	gcc16/lib
BUILDLINK_INCDIRS.gcc16-libatomic=	# no public headers
GCC_REQD+=	16.2
.endif

BUILDLINK_TREE+=	-gcc16-libatomic
