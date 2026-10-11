#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Isolated labwc/V3D client acceptance session.
set -eu
[ "$#" = 2 ] || { echo "Usage: $0 ABSOLUTE_BINARY NEW_WORK" >&2; exit 2; }
binary=$1 work=$2
case "$binary:$work" in /*:/*) ;; *) echo 'Absolute paths required' >&2; exit 2;; esac
src=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
umask 077
mkdir "$work"
mkdir "$work/runtime" "$work/config" "$work/cache" "$work/data" "$work/state"
cat > "$work/client.sh" <<'CLIENT'
#!/bin/sh
set -eu
sh "$EMBER_GPU_RUNNER" "$EMBER_GPU_BINARY" "$(pwd)/client" > client.log 2>&1
CLIENT
cd "$work"
/usr/bin/timeout -k 5 115 /usr/bin/env -i \
    PATH=/usr/pkg/bin:/usr/pkg/sbin:/usr/bin:/usr/sbin:/bin:/sbin HOME="$HOME" \
    XDG_RUNTIME_DIR="$work/runtime" XDG_CONFIG_HOME="$work/config" \
    XDG_CACHE_HOME="$work/cache" XDG_DATA_HOME="$work/data" \
    XDG_STATE_HOME="$work/state" XDG_DATA_DIRS=/usr/pkg/share \
    EMBER_GPU_RUNNER="$src/run.sh" EMBER_GPU_BINARY="$binary" \
    WLR_BACKENDS=headless WLR_HEADLESS_OUTPUTS=1 WLR_RENDERER=gles2 \
    WLR_RENDER_DRM_DEVICE=/dev/dri/renderD128 \
    /usr/pkg/bin/labwc -d -C "$work/config" -S '/bin/sh ./client.sh' > compositor.log 2>&1
cat client.log
grep -q '^PASS: two Qt Quick GPU processes' client.log
grep -q 'GL renderer: V3D ' compositor.log
test -z "$(ls -A runtime)"
echo 'PASS: V3D compositor exited and private Wayland socket removed'
