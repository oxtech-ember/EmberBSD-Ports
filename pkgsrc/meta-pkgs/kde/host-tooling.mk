# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). KDE Frameworks' CMake packages import their
# native code generators from KF6_HOST_TOOLING/<Package>/<Package>*Targets.cmake
# when cross-compiling. Native Ports tool packages install those files below
# TOOLBASE.
#
# used by devel/kf6-kconfig/cross-tools.mk
# used by devel/kf6-kcmutils/cross-tools.mk
# used by security/kf6-kauth/cross-tools.mk
.if !defined(KDE_CROSS_TOOLING_MK)
KDE_CROSS_TOOLING_MK=	yes
CMAKE_CONFIGURE_ARGS+=	-DKF6_HOST_TOOLING=${TOOLBASE}/lib/cmake
.endif
