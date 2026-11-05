# $NetBSD$

BUILDLINK_TREE+=	argparse

.if !defined(ARGPARSE_BUILDLINK3_MK)
ARGPARSE_BUILDLINK3_MK:=

BUILDLINK_API_DEPENDS.argparse+=	argparse>=3.2
BUILDLINK_PKGSRCDIR.argparse?=	../../devel/argparse
BUILDLINK_DEPMETHOD.argparse?=	build
.endif

BUILDLINK_TREE+=	-argparse
