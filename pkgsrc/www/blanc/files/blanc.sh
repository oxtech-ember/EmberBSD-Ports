#!/bin/sh

# Electron 45 reports the system executable as unpackaged by default. This
# upstream-supported override selects the installed application policy.
ELECTRON_FORCE_IS_PACKAGED=1
export ELECTRON_FORCE_IS_PACKAGED

# Plasma Wayland sets XDG_SESSION_TYPE=wayland. Chromium Ozone then prefers
# native Wayland, which exits uncleanly on EmberBSD. Prefer XWayland.
if [ -z "${ELECTRON_OZONE_PLATFORM_HINT}" ]; then
	ELECTRON_OZONE_PLATFORM_HINT=x11
	export ELECTRON_OZONE_PLATFORM_HINT
fi

exec "@PREFIX@/bin/electron" "@PREFIX@/lib/ember-browser/app.asar" "$@"
