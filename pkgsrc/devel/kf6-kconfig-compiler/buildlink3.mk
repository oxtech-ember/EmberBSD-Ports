# $NetBSD$
# Origin: EmberBSD (AI-assisted). Native consumers of devel/kf6-kconfig link
# the generators and KF6ConfigCompilerTargets*.cmake from this package.

BUILDLINK_TREE+=	kf6-kconfig-compiler

.if !defined(KF6_KCONFIG_COMPILER_BUILDLINK3_MK)
KF6_KCONFIG_COMPILER_BUILDLINK3_MK:=

BUILDLINK_API_DEPENDS.kf6-kconfig-compiler+=	kf6-kconfig-compiler>=6.32.0
BUILDLINK_PKGSRCDIR.kf6-kconfig-compiler?=	../../devel/kf6-kconfig-compiler

# KF6ConfigCompilerTargets.cmake imports the programs relative to its prefix.
BUILDLINK_FILES.kf6-kconfig-compiler+=	libexec/kf6/*
.endif	# KF6_KCONFIG_COMPILER_BUILDLINK3_MK

BUILDLINK_TREE+=	-kf6-kconfig-compiler
