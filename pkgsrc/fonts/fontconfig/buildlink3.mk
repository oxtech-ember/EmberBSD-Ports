# $NetBSD: buildlink3.mk,v 1.42 2023/11/12 13:21:26 wiz Exp $

BUILDLINK_TREE+=	fontconfig

.if !defined(FONTCONFIG_BUILDLINK3_MK)
FONTCONFIG_BUILDLINK3_MK:=

BUILDLINK_API_DEPENDS.fontconfig+=	fontconfig>=2.11.91
BUILDLINK_ABI_DEPENDS.fontconfig+=	fontconfig>=2.14.2nb3
BUILDLINK_PKGSRCDIR.fontconfig?=	../../fonts/fontconfig

.include "../../mk/bsd.fast.prefs.mk"
# Static consumers also resolve dladdr used for prefix-owned defaults.
.if !empty(OPSYS:MDarwin) || !empty(OPSYS:MNetBSD) || !empty(OPSYS:MLinux)
.include "../../mk/dlopen.buildlink3.mk"
BUILDLINK_LDFLAGS.fontconfig+=	${DL_LDFLAGS}
BUILDLINK_LIBS.fontconfig+=	${DL_LIBS} ${BUILDLINK_LDADD.dl}
.endif

.include "../../archivers/bzip2/buildlink3.mk"
.include "../../devel/gettext-lib/buildlink3.mk"
.include "../../devel/zlib/buildlink3.mk"
.include "../../graphics/freetype2/buildlink3.mk"
.include "../../textproc/expat/buildlink3.mk"
.endif # FONTCONFIG_BUILDLINK3_MK

BUILDLINK_TREE+=	-fontconfig
