# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Target development files stay in the SDK.
BUILDLINK_TREE+= wayland-devel
.if !defined(WAYLAND_DEVEL_BUILDLINK3_MK)
WAYLAND_DEVEL_BUILDLINK3_MK:=
BUILDLINK_API_DEPENDS.wayland-devel+= wayland-devel>=1.26.0nb2
BUILDLINK_ABI_DEPENDS.wayland-devel+= wayland-devel>=1.26.0nb2
BUILDLINK_PKGSRCDIR.wayland-devel?= ../../devel/wayland-devel
BUILDLINK_DEPMETHOD.wayland-devel= build
.endif
BUILDLINK_TREE+= -wayland-devel
