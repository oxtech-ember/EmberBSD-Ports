# $NetBSD: features.mk,v 1.3 2026/08/19 15:12:51 tsutsui Exp $
# Features of the canonical package, independent of native X11 headers.
MESALIB_SUPPORTS_DRI= yes
MESALIB_SUPPORTS_EGL= yes
MESALIB_SUPPORTS_GLESv2= yes
MESALIB_SUPPORTS_OSMESA= no
MESALIB_SUPPORTS_XA= no
_MESALIB_ARCH_SUPPORTS_XA= no
