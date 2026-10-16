#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Run installed KDED and verify that it executes the target KConfig helper.
set -eu
umask 077
[ "$#" -ge 1 ] && [ "$#" -le 2 ] || {
    echo "Usage: $0 NEW_OUTPUT [PREFIX]" >&2; exit 2;
}
output=$1
prefix=${2:-/usr/pkg}
case "$output:$prefix" in /*:/*) ;; *) echo 'Absolute paths required' >&2; exit 2 ;; esac
[ ! -e "$output" ] && [ ! -L "$output" ] || { echo 'Output exists' >&2; exit 2; }
[ -x "$prefix/bin/kded6" ] && [ -x "$prefix/libexec/kf6/kconf_update" ] || {
    echo 'Installed KDED and KConfig helper are required' >&2; exit 2;
}
mkdir -p "$output"
output=$(CDPATH= cd -- "$output" && pwd -P)
mkdir "$output/home" "$output/config" "$output/data" "$output/cache" "$output/runtime" "$output/empty"
mkdir "$output/data/kconf_update"
cat > "$output/data/kconf_update/ember-runtime-path.upd" <<'UPD'
Version=6
Id=ember-runtime-path
Script=ember-runtime-path.sh,sh
UPD
cat > "$output/data/kconf_update/ember-runtime-path.sh" <<'SCRIPT'
#!/bin/sh
set -eu
printf '%s\n' 'KDED invoked the installed KConfig helper' > "$XDG_CONFIG_HOME/ember-runtime-path-proof"
SCRIPT
printf '%s\n' 'KDED invoked the installed KConfig helper' > "$output/expected"
# --check has no KDBusService registration. All update inputs and outputs are private.
set +e
env -i PATH="$prefix/bin:/bin:/usr/bin" HOME="$output/home" \
    XDG_CONFIG_HOME="$output/config" XDG_DATA_HOME="$output/data" \
    XDG_CACHE_HOME="$output/cache" XDG_RUNTIME_DIR="$output/runtime" \
    XDG_CONFIG_DIRS="$output/empty" XDG_DATA_DIRS="$output/empty" \
    DBUS_SESSION_BUS_ADDRESS="unix:path=$output/absent-bus" \
    QT_QPA_PLATFORM=offscreen "$prefix/bin/kded6" --check > "$output/kded.log" 2>&1
status=$?
set -e
printf '%s\n' "$status" > "$output/exit-status"
[ "$status" -eq 0 ] || { echo "FAIL: kded6 --check exited $status" >&2; exit 1; }
# Upstream KDED returns 0 even if the helper failed. Require the real side effect.
[ -f "$output/config/ember-runtime-path-proof" ] && \
    cmp -s "$output/expected" "$output/config/ember-runtime-path-proof" || {
    echo 'FAIL: KDED did not execute the installed helper and private update script' >&2; exit 1;
}
echo 'PASS: installed KDED executed the target KConfig helper in an isolated configuration'
