# $NetBSD: buildlink3.mk,v 1.1 2021/07/27 09:29:41 fcambus Exp $

BUILDLINK_TREE+=	mimalloc

.if !defined(MIMALLOC_BUILDLINK3_MK)
MIMALLOC_BUILDLINK3_MK:=

BUILDLINK_API_DEPENDS.mimalloc+=	mimalloc>=3.6.0
BUILDLINK_ABI_DEPENDS.mimalloc+=	mimalloc>=3.6.0
BUILDLINK_PKGSRCDIR.mimalloc?=	../../devel/mimalloc

# Consumers declare policy; they must not silently rebuild or substitute the
# selected provider. Defer refusals to configure so fetching needs no library.
pkgbase := mimalloc
.include "../../mk/pkg-build-options.mk"

pre-configure: ember-mimalloc-consumer-options
.PHONY: ember-mimalloc-consumer-options
ember-mimalloc-consumer-options:
.if ${MIMALLOC_REQUIRE_OVERRIDE:U} == "yes" && empty(PKG_BUILD_OPTIONS.mimalloc:Mmalloc-override)
	${FAIL_MSG} "This consumer requires mimalloc's malloc-override option"
.elif ${MIMALLOC_REQUIRE_OVERRIDE:U} == "no" && !empty(PKG_BUILD_OPTIONS.mimalloc:Mmalloc-override)
	${FAIL_MSG} "This consumer requires mimalloc without malloc-override"
.elif !empty(MIMALLOC_REQUIRE_OVERRIDE:U) && ${MIMALLOC_REQUIRE_OVERRIDE} != "yes" && ${MIMALLOC_REQUIRE_OVERRIDE} != "no"
	${FAIL_MSG} "MIMALLOC_REQUIRE_OVERRIDE must be yes, no or unset"
.endif
.if ${MIMALLOC_REQUIRE_DYNAMIC_TLS:Uno} == "yes" && empty(PKG_BUILD_OPTIONS.mimalloc:Mdynamic-tls)
	${FAIL_MSG} "This consumer requires mimalloc's dynamic-tls option"
.endif
.if ${MIMALLOC_REQUIRE_GENERIC_ARCH:Uno} == "yes" && empty(PKG_BUILD_OPTIONS.mimalloc:Mgeneric-arch)
	${FAIL_MSG} "This consumer requires mimalloc's generic-arch option"
.endif
	@${TRUE}
.endif	# MIMALLOC_BUILDLINK3_MK

BUILDLINK_TREE+=	-mimalloc
