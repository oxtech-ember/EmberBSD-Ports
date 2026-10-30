# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), native KAuth policy generator.
.if !defined(EMBERBSD_KF6_KAUTH_CROSS_MK)
EMBERBSD_KF6_KAUTH_CROSS_MK=	yes
.include "../../mk/bsd.prefs.mk"
.if ${USE_CROSS_COMPILE:Uno:tl} == "yes"
# KF6::kauth-policy-gen runs on the build host. It comes from
# security/kf6-kauth-policy-gen, a native package of the same release, and
# KF6AuthConfig.cmake imports it from KF6_HOST_TOOLING.
TOOL_DEPENDS+=	kf6-kauth-policy-gen-6.31.0{,nb[0-9]*}:../../security/kf6-kauth-policy-gen
.include "../../meta-pkgs/kde/host-tooling.mk"
.endif
.endif
