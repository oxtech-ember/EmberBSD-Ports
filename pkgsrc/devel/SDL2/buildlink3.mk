# SPDX-License-Identifier: BSD-2-Clause
BUILDLINK_TREE+=	SDL2

.if !defined(SDL2_BUILDLINK3_MK)
SDL2_BUILDLINK3_MK:=

BUILDLINK_API_DEPENDS.SDL2+=	SDL2>=2.0
BUILDLINK_ABI_DEPENDS.SDL2+=	SDL2>=2.32.74
BUILDLINK_PKGSRCDIR.SDL2?=	../../devel/SDL2
BUILDLINK_INCDIRS.SDL2+=	include/SDL2

.if ${USE_CROSS_COMPILE:tl} == "yes"
# sdl2-config is a shell script that we need to run at build-time to
# learn about the target system's SDL2 toolchain options.
TOOLS_CREATE+=		sdl2-config
TOOLS_PATH.sdl2-config=	${CROSS_DESTDIR}${LOCALBASE}/bin/sdl2-config
.endif

.include "../../devel/SDL3/buildlink3.mk"
# SDL2 programs get the features of the SDL3 that runs them.
PKG_BUILD_OPTIONS.SDL2=	${PKG_BUILD_OPTIONS.SDL3}

.endif	# SDL2_BUILDLINK3_MK

BUILDLINK_TREE+=	-SDL2
