# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), reuse the matching build-host scanner.
.if empty(EMBERBSD_WAYLAND_SCANNER:M/*) || !exists(${EMBERBSD_WAYLAND_SCANNER})
PKG_FAIL_REASON+= "EMBERBSD_WAYLAND_SCANNER must name an existing absolute executable"
.else
_EMBERBSD_SCANNER_VALID!= if test -x ${EMBERBSD_WAYLAND_SCANNER:Q} && \
    ember_scanner_banner=$$(${EMBERBSD_WAYLAND_SCANNER:Q} --version 2>&1) && \
    test "$$ember_scanner_banner" = 'wayland-scanner 1.26.0'; then \
    printf '%s\n' yes; else printf '%s\n' no; fi
.if ${_EMBERBSD_SCANNER_VALID} != "yes"
PKG_FAIL_REASON+= "The build-host wayland-scanner must execute and report exactly 1.26.0"
.endif
.endif
