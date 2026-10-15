#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Detect an omitted modules repair, wrong C++ SONAME selection or leaked
# native-driver patch by preparing actual source files with tar and patch.
set -eu
here=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd -P)
[ -f "$here/prepare-source.sh" ] || { echo 'FAIL: audited runtime source preparation is missing' >&2; exit 1; }
work=$(mktemp -d /tmp/ember-gcc-runtime-source.XXXXXX)
trap 'rm -rf "$work"' EXIT HUP INT TERM
mkdir -p "$work/profile/bootstrap" "$work/pkgsrc/lang/gcc16/patches" \
    "$work/gcc-16.2.0/gcc" "$work/gcc-16.2.0/libstdc++-v3"
cp "$here"/*.sh "$work/profile/bootstrap/"
printf 'original modules\n' > "$work/gcc-16.2.0/gcc/module.cc"
printf 'native driver untouched\n' > "$work/gcc-16.2.0/gcc/Makefile.in"
printf '#!/bin/sh\nlibtool_VERSION=6:36:0\n' > "$work/gcc-16.2.0/libstdc++-v3/configure"
chmod +x "$work/gcc-16.2.0/libstdc++-v3/configure"
tar -cf "$work/gcc.tar" -C "$work" gcc-16.2.0
hash=$(shasum -a 256 "$work/gcc.tar" | awk '{print $1}')
printf 'gcc\t16.2.0\thttps://example.invalid/gcc.tar\t%s\n' "$hash" > "$work/profile/sources.tsv"
recipe=$work/pkgsrc/lang/gcc16
printf "CONFIGURE_ARGS+= --disable-libssp\nSUBST_SED.libstdc= -e 's,libtool_VERSION=6:,libtool_VERSION=7:,g'\n" > "$recipe/Makefile"
cat > "$recipe/patches/patch-gcc_cp_module.cc" <<'EOF'
--- gcc/module.cc.orig
+++ gcc/module.cc
@@ -1 +1 @@
-original modules
+repaired modules
EOF
cat > "$recipe/patches/patch-gcc_Makefile.in" <<'EOF'
--- gcc/Makefile.in.orig
+++ gcc/Makefile.in
@@ -1 +1 @@
-native driver untouched
+native driver embeds /host/prefix
EOF
for name in patch-gcc_cp_module.cc patch-gcc_Makefile.in; do
    hash=$(shasum -a 1 "$recipe/patches/$name" | awk '{print $1}')
    printf 'SHA1 (%s) = %s\n' "$name" "$hash" >> "$recipe/distinfo"
done
sh "$work/profile/bootstrap/prepare-source.sh" "$work/pkgsrc" "$work/gcc.tar" "$work/prepared"
grep -qx 'repaired modules' "$work/prepared/gcc/module.cc"
grep -qx 'native driver untouched' "$work/prepared/gcc/Makefile.in"
grep -qx 'libtool_VERSION=7:36:0' "$work/prepared/libstdc++-v3/configure"
[ -x "$work/prepared/libstdc++-v3/configure" ]
if sh "$work/profile/bootstrap/prepare-source.sh" "$work/pkgsrc" "$work/gcc.tar" "$work/prepared" > "$work/repeat.log" 2>&1; then
    echo 'FAIL: overwrote an existing source tree' >&2; exit 1
fi
printf 'corruption\n' >> "$work/gcc.tar"
if sh "$work/profile/bootstrap/prepare-source.sh" "$work/pkgsrc" "$work/gcc.tar" "$work/rejected" > "$work/corrupt.log" 2>&1; then
    echo 'FAIL: accepted a corrupt source archive' >&2; exit 1
fi
[ ! -e "$work/rejected" ]
echo 'PASS: real archive, patch, ABI substitution and source ownership checks'
