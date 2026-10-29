# $NetBSD$
BUILDLINK_TREE+= openddl-parser
.if !defined(OPENDDL_PARSER_BUILDLINK3_MK)
OPENDDL_PARSER_BUILDLINK3_MK:=
BUILDLINK_API_DEPENDS.openddl-parser+= openddl-parser>=0.5.2
.if ${OPSYS} == "Darwin" && ${USE_CROSS_COMPILE:Uno:tl} != "yes" && \
    ${EMBERBSD_NATIVE_CXX_ABI_NAMESPACE:U} == "__ember1"
BUILDLINK_ABI_DEPENDS.openddl-parser+= openddl-parser>=0.5.2nb1
.endif
BUILDLINK_PKGSRCDIR.openddl-parser?= ../../devel/openddl-parser
.endif
BUILDLINK_TREE+= -openddl-parser
