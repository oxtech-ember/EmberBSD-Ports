#!/bin/sh

# Electron 44 reports the system executable as unpackaged by default. This
# upstream-supported override selects the installed application policy.
ELECTRON_FORCE_IS_PACKAGED=1
export ELECTRON_FORCE_IS_PACKAGED
exec "@PREFIX@/bin/electron" "@PREFIX@/lib/blanc/app.asar" "$@"
