#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), actual recipe scanner-selection guards.
set -eu
[ "$#" = 2 ] || { echo "Usage: $0 REAL_HOST_SCANNER NEW_ABSOLUTE_WORK" >&2; exit 2; }
scanner=$1 work=$2
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
make=$(command -v "${BMAKE:-bmake}")
case "$scanner:$work:$make" in /*:/*:/*) ;; *) exit 2;; esac
[ "$("$scanner" --version 2>&1)" = 'wayland-scanner 1.26.0' ]
mkdir "$work"
printf '.include "%s/../../pkgsrc/devel/wayland/cross-scanner.mk"\n' "$root" > "$work/check.mk"
check() {
    name=$1 tool=$2 expected=$3
    "$make" -f "$work/check.mk" "EMBERBSD_WAYLAND_SCANNER=$tool" \
        -V PKG_FAIL_REASON > "$work/$name.log" 2>&1
    if [ "$expected" = pass ]; then
        [ -z "$(cat "$work/$name.log")" ]
    else
        grep -q 'must' "$work/$name.log"
    fi
}
check matching "$scanner" pass
check absent "$work/missing" fail
check relative scanner fail
cat > "$work/old" <<'SH'
#!/bin/sh
echo 'wayland-scanner 1.25.0' >&2
SH
cat > "$work/failed" <<'SH'
#!/bin/sh
echo 'wayland-scanner 1.26.0' >&2
exit 1
SH
cat > "$work/extra" <<'SH'
#!/bin/sh
echo 'wayland-scanner 1.26.0'
echo 'unexpected metadata'
SH
chmod +x "$work/old" "$work/failed" "$work/extra"
check old "$work/old" fail
check failed "$work/failed" fail
check extra "$work/extra" fail
cp "$work/old" "$work/nonexecutable"
chmod -x "$work/nonexecutable"
check nonexecutable "$work/nonexecutable" fail
shasum -a 256 "$0" "$root/../../pkgsrc/devel/wayland/cross-scanner.mk" \
    "$scanner" "$make" > "$work/inputs.sha256"
echo 'PASS: real matching scanner accepted; six invalid selections rejected'
