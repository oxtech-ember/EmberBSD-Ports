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

# Keep this process on X11/XWayland. Leaving Wayland session variables set
# lets Chromium mix Ozone X11 with Wayland display state and drop the window.
XDG_SESSION_TYPE=x11
export XDG_SESSION_TYPE
unset WAYLAND_DISPLAY

# Force Ozone X11 and keep the GPU process in-tree unless the caller set them.
# Hardware GL stays on: ANGLE binds Mesa radeonsi under XWayland on Nick.
ozone_platform_set=no
in_process_gpu_set=no
for arg in "$@"; do
	case "${arg}" in
	--ozone-platform|--ozone-platform=*)
		ozone_platform_set=yes
		;;
	--in-process-gpu|--in-process-gpu=*)
		in_process_gpu_set=yes
		;;
	esac
done
if [ "${ozone_platform_set}" = "no" ]; then
	set -- --ozone-platform=x11 "$@"
fi
if [ "${in_process_gpu_set}" = "no" ]; then
	set -- --in-process-gpu "$@"
fi

config_home="${XDG_CONFIG_HOME:-${HOME}/.config}"
app_config="${config_home}/Ember Browser"
local_state="${app_config}/Local State"
crash_ledger="${app_config}/crash-ledger.json"

# Stale GPU/Dawn caches recreate invalid bounds after Ozone/XWayland crashes.
# Drop only those caches; keep bookmarks, settings and session files.
for d in GPUCache GPUPersistentCache DawnGraphiteCache DawnWebGPUCache; do
	if [ -e "${app_config}/${d}" ]; then
		rm -rf "${app_config}/${d}"
	fi
done

# Drop invalid Electron windowStates. Zero-sized or inverted bounds make the
# window vanish and Blanc exit; recoveryPending requests a fresh geometry.
py="@PREFIX@/bin/python3.15"
if [ -f "${local_state}" ] && [ -x "${py}" ]; then
	EMBER_BROWSER_LOCAL_STATE="${local_state}" \
	EMBER_BROWSER_CRASH_LEDGER="${crash_ledger}" \
	"${py}" -c '
import json, os
from pathlib import Path

path = Path(os.environ["EMBER_BROWSER_LOCAL_STATE"])
ledger_path = Path(os.environ.get("EMBER_BROWSER_CRASH_LEDGER", ""))
try:
    data = json.loads(path.read_text())
except Exception:
    raise SystemExit(0)

states = data.get("windowStates")
if not isinstance(states, dict) or not states:
    raise SystemExit(0)

def invalid(st):
    if not isinstance(st, dict):
        return True
    try:
        width = int(st.get("right", 0)) - int(st.get("left", 0))
        height = int(st.get("bottom", 0)) - int(st.get("top", 0))
    except Exception:
        return True
    return width <= 0 or height <= 0

bad = any(invalid(st) for st in states.values())
recover = False
if ledger_path.is_file():
    try:
        ledger = json.loads(ledger_path.read_text())
    except Exception:
        ledger = {}
    if ledger.get("recoveryPending") is True:
        recover = True

if not (bad or recover):
    raise SystemExit(0)

backup = path.with_name(path.name + ".bak-ozone-x11")
if not backup.exists():
    backup.write_text(path.read_text())
del data["windowStates"]
path.write_text(json.dumps(data, separators=(",", ":")))
'
fi

exec "@PREFIX@/bin/electron" "@PREFIX@/lib/ember-browser/app.asar" "$@"
