# $NetBSD: buildlink3.mk,v 1.18 2026/09/02 19:01:26 wiz Exp $

BUILDLINK_TREE+=	gobject-introspection

.if !defined(GOBJECT_INTROSPECTION_BUILDLINK3_MK)
GOBJECT_INTROSPECTION_BUILDLINK3_MK:=

BUILDLINK_API_DEPENDS.gobject-introspection+=	gobject-introspection>=0.6.14nb1
BUILDLINK_ABI_DEPENDS.gobject-introspection+=	gobject-introspection>=1.86.0nb6
BUILDLINK_PKGSRCDIR.gobject-introspection?=	../../devel/gobject-introspection

ALL_ENV+=	GI_SCANNER_DISABLE_CACHE=yes
.include "../../devel/gobject-introspection/native-stage-loader.mk"
.if !empty(_EMBERBSD_NATIVE_RUNTIME_SUFFIX)
BUILDLINK_ABI_DEPENDS.gobject-introspection+= gobject-introspection>=1.86.0nb9
.  if !empty(XDG_DATA_DIRS:U)
.    if !empty(XDG_DATA_DIRS:M\:*) || !empty(XDG_DATA_DIRS:M*\:) || !empty(XDG_DATA_DIRS:M*\:\:*)
.      error XDG_DATA_DIRS must not contain empty path components
.    endif
MAKE_ENV+= XDG_DATA_DIRS=${EMBERBSD_NATIVE_STAGE_ROOT:Q}${EMBERBSD_NATIVE_STAGE_PREFIX:Q}/share:${XDG_DATA_DIRS:Q}
.  else
MAKE_ENV+= XDG_DATA_DIRS=${EMBERBSD_NATIVE_STAGE_ROOT:Q}${EMBERBSD_NATIVE_STAGE_PREFIX:Q}/share:${PREFIX:Q}/share
.  endif
.endif

.if !${BUILDLINK_DEPMETHOD.gobject-introspection:U:Mbuild}
.include "../../devel/glib2/buildlink3.mk"
.include "../../devel/libffi/buildlink3.mk"
.endif

.endif	# GOBJECT_INTROSPECTION_BUILDLINK3_MK

BUILDLINK_TREE+=	-gobject-introspection
