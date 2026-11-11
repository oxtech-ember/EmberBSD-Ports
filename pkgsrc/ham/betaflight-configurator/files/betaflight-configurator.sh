#!/bin/sh
ELECTRON_FORCE_IS_PACKAGED=1
export ELECTRON_FORCE_IS_PACKAGED
if [ -z "${ELECTRON_OZONE_PLATFORM_HINT}" ]; then
	ELECTRON_OZONE_PLATFORM_HINT=x11
	export ELECTRON_OZONE_PLATFORM_HINT
fi
XDG_SESSION_TYPE=x11
export XDG_SESSION_TYPE
unset WAYLAND_DISPLAY
ozone_platform_set=no
in_process_gpu_set=no
for arg in "$@"; do
	case "${arg}" in
	--ozone-platform|--ozone-platform=*) ozone_platform_set=yes ;;
	--in-process-gpu|--in-process-gpu=*) in_process_gpu_set=yes ;;
	esac
done
if [ "${ozone_platform_set}" = "no" ]; then
	set -- --ozone-platform=x11 "$@"
fi
if [ "${in_process_gpu_set}" = "no" ]; then
	set -- --in-process-gpu "$@"
fi
exec "@PREFIX@/bin/electron" "@PREFIX@/lib/betaflight-configurator/app.asar" "$@"
