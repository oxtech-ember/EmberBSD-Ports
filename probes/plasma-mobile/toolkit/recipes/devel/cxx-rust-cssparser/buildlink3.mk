# $NetBSD$

BUILDLINK_TREE+=	cxx-rust-cssparser

.if !defined(CXX_RUST_CSSPARSER_BUILDLINK3_MK)
CXX_RUST_CSSPARSER_BUILDLINK3_MK:=

BUILDLINK_API_DEPENDS.cxx-rust-cssparser+=	cxx-rust-cssparser>=1.1.0
BUILDLINK_PKGSRCDIR.cxx-rust-cssparser?=	../../devel/cxx-rust-cssparser

.include "../../mk/pthread.buildlink3.mk"
.endif # CXX_RUST_CSSPARSER_BUILDLINK3_MK

BUILDLINK_TREE+=	-cxx-rust-cssparser
