#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Exercise the real recipe's native-tool guard.
set -eu
[ "$#" = 3 ] || { echo "Usage: $0 PREPARED_PKGSRC HOST_QT NEW_WORK" >&2; exit 2; }
pkgsrc=$1 host=$2 work=$3
: "${BMAKE:?Set the native bmake executable}"
: "${MAKECONF:?Set the configured cross-package MAKECONF}"
mkdir "$work"
recipe=$pkgsrc/devel/kf6-kcoreaddons
"$BMAKE" -C "$recipe" "EMBERBSD_QT_HOST_PATH=$host" emberbsd-native-linguist-check > "$work/valid.log" 2>&1
"$BMAKE" -C "$recipe" -V '${DEPENDS}' > "$work/dependencies.txt"
! grep -q 'qt6-qttools' "$work/dependencies.txt"
grep -q 'qt6-qtdeclarative>=6.12.0' "$work/dependencies.txt"
mkdir "$work/old" "$work/old/bin"
cat > "$work/old/bin/lrelease" <<'TOOL'
#!/bin/sh
echo 'lrelease version 6.11.2'
TOOL
cp "$work/old/bin/lrelease" "$work/old/bin/lconvert"
chmod +x "$work/old/bin/lrelease" "$work/old/bin/lconvert"
for bad in "$work/old" "$work/missing"; do
    if "$BMAKE" -C "$recipe" "EMBERBSD_QT_HOST_PATH=$bad" emberbsd-native-linguist-check > "$work/invalid-${bad##*/}.log" 2>&1; then
        echo 'Invalid host tools accepted' >&2; exit 1
    fi
    grep -q 'Matching native Qt 6.12 Linguist tools are required' "$work/invalid-${bad##*/}.log"
done
echo 'PASS: current native Linguist accepted; old/missing tools rejected; target QML dependency preserved'
