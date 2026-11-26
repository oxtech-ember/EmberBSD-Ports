#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Source planning exposes exact package identities without another metadata walk.
set -eu
out=$1
ports=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd -P)
sh "$ports/scripts/tests/cross-bulk-selected-build.sh" "$out" > "$out.log" 2>&1
printf '%s\n' cat/app > "$out/roots"
BMAKE="$out/bmake" MAKECONF="$out/mk.conf" PKGSRCDIR="$out/tree" \
    sh "$ports/scripts/cross-bulk.sh" selected-order "$out/roots" "$out/state" > "$out/order-binary.log" 2>&1
grep -qx 'cat/app app-1.0' "$out/state/packages"
grep -qx 'cat/dep dep-1.0' "$out/state/packages"
# A signed-binary selection only permits exact names that remain installed.
cat > "$out/pkg_info" <<'WRAPPER'
#!/bin/sh
for arg do
    case "$arg" in app-1.0|dep-1.0) exit 0 ;; esac
done
exit 1
WRAPPER
cp "$out/state/packages" "$out/binary-installed"
rm -f "$out/state/done" "$out/packages/All/app-1.0.tgz" "$out/packages/All/dep-1.0.tgz"
: > "$out/targets"
BMAKE="$out/bmake" MAKECONF="$out/mk.conf" PKGSRCDIR="$out/tree" \
    CROSS_BULK_BINARY_INSTALLED="$out/binary-installed" \
    sh "$ports/scripts/cross-bulk.sh" selected-build "$out/roots" "$out/state" > "$out/build-binary.log" 2>&1
[ ! -s "$out/targets" ] || { echo 'Installed binaries were rebuilt' >&2; exit 1; }
# A new SDK selection file must use the same package metadata as its predecessor.
mv "$out/bmake" "$out/bmake-fixture"
cat > "$out/bmake" <<'WRAPPER'
#!/bin/sh
if [ "${CROSS_BULK_BINARY_INSTALLED+x}" = x ]; then
    echo 'The SDK selection reached bmake' >&2
    exit 1
fi
exec "${0%/*}/bmake-fixture" "$@"
WRAPPER
chmod +x "$out/bmake"
build_with_selection()
{
    BMAKE="$out/bmake" MAKECONF="$out/mk.conf" PKGSRCDIR="$out/tree" \
        CROSS_BULK_BINARY_INSTALLED="$1" \
        sh "$ports/scripts/cross-bulk.sh" build "$out/state/order" "$out/state"
}
cp "$out/binary-installed" "$out/next-selection"
build_with_selection "$out/binary-installed" > "$out/first-manifest.log" 2>&1
: > "$out/calls"
build_with_selection "$out/next-selection" > "$out/next-manifest.log" 2>&1
if grep -E '/cat/(app|dep) show-vars$' "$out/calls" >&2; then
    echo 'Changing the SDK selection file repeated the package metadata queries' >&2
    exit 1
fi
[ ! -s "$out/targets" ] || { echo 'Installed binaries were rebuilt' >&2; exit 1; }
printf '%s\n' 'PASS: source graph identities and installed binary reuse'
