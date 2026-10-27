# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), reuse the matching native Ports scanner.
.if !defined(EMBERBSD_WAYLAND_SCANNER_CHECK_MK)
EMBERBSD_WAYLAND_SCANNER_CHECK_MK=
# The selector itself consumes the shared native Python, including consumers
# such as wlroots that otherwise need no Python tool.
.include "../../lang/python/tool.mk"
_EMBERBSD_WAYLAND_SCANNER_CHECKER:= ${.PARSEDIR:tA}/files/check-host-scanner.py

# Source acquisition does not require an installed generator. The ordinary
# native recipe owns it; selection runs before target configuration.
pre-configure: emberbsd-wayland-scanner-check
.PHONY: emberbsd-wayland-scanner-check
emberbsd-wayland-scanner-check:
	${RUN} ember_scanner_python=${TOOL_PYTHONBIN:U:Q}; \
	test -n "$$ember_scanner_python" && test -x "$$ember_scanner_python" || { \
	    echo 'Wayland scanner selection requires the native Python tool' >&2; exit 1; \
	}; \
	"$$ember_scanner_python" -B -I -S ${_EMBERBSD_WAYLAND_SCANNER_CHECKER:Q} \
	    --sdk-source ${EMBERBSD_SDK_SOURCE:Q} --host-prefix ${TOOLBASE:Q} \
	    --scanner ${EMBERBSD_WAYLAND_SCANNER:Q} --pkg-config ${TOOLBASE:Q}/bin/pkg-config
.endif
