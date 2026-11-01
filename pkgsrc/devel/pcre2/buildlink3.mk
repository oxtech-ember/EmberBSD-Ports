# $NetBSD: buildlink3.mk,v 1.8 2026/09/02 19:00:41 wiz Exp $

BUILDLINK_TREE+=	pcre2

.if !defined(PCRE2_BUILDLINK3_MK)
PCRE2_BUILDLINK3_MK:=

BUILDLINK_API_DEPENDS.pcre2+=	pcre2>=10.21
BUILDLINK_ABI_DEPENDS.pcre2+=	pcre2>=10.49
BUILDLINK_PKGSRCDIR.pcre2?=	../../devel/pcre2

# Consumers pass PCRE2_CONFIG to configure as the pcre2-config to run.
.if ${USE_CROSS_COMPILE:Uno:tl} == "yes"
# The installed pcre2-config is the target's, under the target prefix that
# the build host does not have, and configure (apache24) looks only for
# ${target_alias}-pcre2-config in a cross build. Run a copy of it; its
# output names the target prefix, which the compiler wrappers map to the
# build sysroot.
PCRE2_CONFIG=		${WRKDIR}/.pcre2-cross/bin/pcre2-config

pre-configure: pcre2-cross-config

.PHONY: pcre2-cross-config
pcre2-cross-config:
	${RUN}${MKDIR} ${PCRE2_CONFIG:H}
	${RUN}${CP} ${_CROSS_DESTDIR}${BUILDLINK_PREFIX.pcre2}/bin/pcre2-config \
		${PCRE2_CONFIG}.tmp
	${RUN}${CHMOD} +x ${PCRE2_CONFIG}.tmp
	${RUN}${MV} -f ${PCRE2_CONFIG}.tmp ${PCRE2_CONFIG}
.else
PCRE2_CONFIG?=		${BUILDLINK_PREFIX.pcre2}/bin/pcre2-config
.endif
.endif	# PCRE2_BUILDLINK3_MK

BUILDLINK_TREE+=	-pcre2
