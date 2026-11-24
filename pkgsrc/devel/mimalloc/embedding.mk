# $NetBSD$
# Select the shared allocator for a plugin that must preserve its host allocator.
.include "../../mk/bsd.fast.prefs.mk"

.if ${OPSYS} == "Darwin"
BUILDLINK_ABI_DEPENDS.mimalloc+=	mimalloc>=3.7.0nb1
MIMALLOC_EMBED_LIBRARY=	mimalloc-embed
.else
MIMALLOC_REQUIRE_OVERRIDE=	no
MIMALLOC_EMBED_LIBRARY=	mimalloc
.endif

.include "../../devel/mimalloc/buildlink3.mk"
