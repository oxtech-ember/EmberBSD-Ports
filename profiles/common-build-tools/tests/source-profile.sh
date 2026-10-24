#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD, AI-assisted source and profile integration regression.
set -eu
[ "$#" -ge 2 ] && [ "$#" -le 3 ] || { echo "Usage: $0 VERIFIED_DISTFILES NEW_WORK [python-source|llvm-source]" >&2; exit 2; }
scope=${3:-all}
case "$scope" in all|python-source|llvm-source) ;; *) echo 'Unknown source gate.' >&2; exit 2 ;; esac
root=$(CDPATH= cd -- "$(dirname -- "$0")/../../.." && pwd)
if [ "$scope" = llvm-source ]; then
    exec sh "$root/profiles/common-build-tools/tests/llvm-source.sh" "$1" "$2"
fi
if [ "$scope" = python-source ]; then
    exec "${PYTHON:-python3}" -B "$root/profiles/common-build-tools/tests/python-source.py" "$1" "$2"
fi
distfiles=$(CDPATH= cd -- "$1" && pwd)
mkdir "$2"
work=$(CDPATH= cd -- "$2" && pwd)
case "$work:$distfiles" in *[!a-zA-Z0-9_./:-]*) echo 'Use paths without shell metacharacters.' >&2; exit 2 ;; esac
profile=$root/profiles/common-build-tools
cat > "$work/digest" <<'DIGEST'
#!/bin/sh
algorithm=$1
shift
if [ "$#" -eq 0 ]; then
    [ "$algorithm" = SHA1 ] || exit 2
    shasum -a 1 | awk '{print $1}'
    exit
fi
for file do
    case "$algorithm" in
        SHA512) hash=$(shasum -a 512 "$file" | awk '{print $1}') ;;
        BLAKE2s) hash=$("${OPENSSL:-openssl}" dgst -blake2s256 "$file" | awk '{print $NF}') ;;
        *) exit 2 ;;
    esac
    printf '%s (%s) = %s\n' "$algorithm" "$file" "$hash"
done
DIGEST
chmod +x "$work/digest"
export DIGEST=$work/digest
verifier=$root/upstream/pkgsrc/mk/checksum/checksum.awk
while IFS="$(printf '\t')" read -r archive sha url; do
    case "$archive" in ''|'#'*) continue ;; esac
    [ "$(shasum -a 256 "$distfiles/$archive" | awk '{print $1}')" = "$sha" ]
done < "$profile/sources.tsv"
recipe=$root/pkgsrc/devel/meson
archive=meson-1.12.1.tar.gz
awk '/^SHA1 \(patch-/ { gsub(/[()]/, "", $2); print $2 }' "$recipe/distinfo" > "$work/required-patches"
while read -r required; do [ -f "$recipe/patches/$required" ]; done < "$work/required-patches"
(cd "$distfiles" && awk -f "$verifier" -- "$recipe/distinfo" "$archive")
recorded=$(awk -v name="($archive)" '$1 == "Size" && $2 == name {print $4}' "$recipe/distinfo")
[ "$(wc -c < "$distfiles/$archive" | tr -d ' ')" = "$recorded" ]
awk -f "$verifier" -- -p "$recipe/distinfo" "$recipe"/patches/patch-*
# Keep the common Meson checksum refusal cases. The Python gate owns its cases.
cp "$distfiles/$archive" "$work/$archive"
printf x >> "$work/$archive"
if (cd "$work" && awk -f "$verifier" -- "$recipe/distinfo" "$archive") > "$work/corrupt.log" 2>&1; then exit 1; fi
first=$(find "$recipe/patches" -type f -name 'patch-*' | LC_ALL=C sort | sed -n '1p')
name=${first##*/}
raw=$(shasum -a 1 "$first" | awk '{print $1}')
sed "s/^SHA1 ($name) = .*/SHA1 ($name) = $raw/" "$recipe/distinfo" > "$work/raw-distinfo"
if awk -f "$verifier" -- -p "$work/raw-distinfo" "$first" > "$work/raw.log" 2>&1; then exit 1; fi
if awk -f "$verifier" -- -p "$recipe/distinfo" "$work/$name" > "$work/missing.log" 2>&1; then exit 1; fi
mkdir "$work/meson-patched" "$work/meson-pristine"
tar -xf "$distfiles/$archive" --strip-components=1 -C "$work/meson-pristine"
cp -R "$work/meson-pristine/." "$work/meson-patched/"
for delta in "$recipe"/patches/patch-*; do
    patch -f -N -F 0 -p0 -d "$work/meson-patched" < "$delta"
done
if patch -f -N -F 0 -p0 -d "$work/meson-patched" < "$first" > "$work/repeat-meson-patched.log" 2>&1; then
    echo 'FAIL: repeated patch accepted' >&2; exit 1
fi
cmp "$root/upstream/pkgsrc/devel/meson/PLIST" "$recipe/PLIST"
# The dropped ELF depfixer patch must leave this upstream implementation exact.
cmp "$work/meson-pristine/mesonbuild/scripts/depfixer.py" "$work/meson-patched/mesonbuild/scripts/depfixer.py"
"$PY" -B "$root/scripts/tests/export-fixture.py" "$root" "$work/pkgsrc" > "$work/export.log"
diff -r "$recipe" "$work/pkgsrc/devel/meson"
# Both entry points use the current canonical Python recipe and the normal export.
"${PYTHON:-python3}" -B "$profile/tests/python-source.py" "$distfiles" "$work/python" --pkgsrc "$work/pkgsrc"
# Existing GCC recipes must remain byte-for-byte identical to the established
# development profile recipes.
mkdir "$work/gcc-reference"
git -C "$root/upstream/pkgsrc" archive HEAD lang/gcc16 lang/gcc16-libs lang/gcc16-libjit \
    math/mpfr math/mpcomplex devel/gtexinfo lang/tcl-expect | tar -xf - -C "$work/gcc-reference"
for delta in pkgsrc-gcc16.2.patch strict-tests.patch current-prerequisites.patch stable-expect.patch gcc-tsvc-netbsd.patch; do
    patch -f -E -F 0 -p1 -d "$work/gcc-reference" < \
        "$root/profiles/development-toolchain/patches/$delta" >> "$work/gcc-export.log"
done
rm -rf "$work/gcc-reference/devel/gtexinfo"
cp -R "$root/pkgsrc/devel/gtexinfo" "$work/gcc-reference/devel/gtexinfo"
for recipe in lang/gcc16 lang/gcc16-libs lang/gcc16-libjit math/mpfr math/mpcomplex devel/gtexinfo lang/tcl-expect; do
    diff -r "$work/gcc-reference/$recipe" "$work/pkgsrc/$recipe"
done
cmp "$root/profiles/development-toolchain/mk.conf" "$work/pkgsrc/EMBERBSD-DEVELOPMENT-MK.CONF"
if "$PY" -B "$root/scripts/tests/export-fixture.py" "$root" "$work/pkgsrc" > "$work/existing.log" 2>&1; then exit 1; fi
if "$PY" -B "$root/scripts/tests/export-fixture.py" "$root" "$work/unknown" invalid > "$work/unknown.log" 2>&1; then exit 1; fi
[ ! -e "$work/unknown" ]
# A private exporter fixture removes one required patch, never the real recipe.
fixture=$work/missing-fixture
mkdir -p "$fixture/scripts" "$fixture/upstream"
cp "$root/scripts/prepare-pkgsrc.sh" "$root/scripts/prepare-pkgsrc.py" "$fixture/scripts/"
for item in profiles probes; do cp -R "$root/$item" "$fixture/$item"; done
# Keep recipe links and their shared patch targets inside the fixture.
cp -R "$root/pkgsrc" "$fixture/pkgsrc"
ln -s "$root/upstream/pkgsrc" "$fixture/upstream/pkgsrc"
git -C "$fixture" init -q
pin=$(git -C "$root/upstream/pkgsrc" rev-parse HEAD)
git -C "$fixture" update-index --add --cacheinfo "160000,$pin,upstream/pkgsrc"
missing=$(cd "$fixture/pkgsrc/devel/meson/patches" && ls patch-* | head -n 1)
rm "$fixture/pkgsrc/devel/meson/patches/$missing"
if "$PY" -B "$root/scripts/tests/export-fixture.py" "$fixture" "$work/missing-export" > "$work/missing-export.log" 2>&1; then exit 1; fi
grep -qF "Missing patch: pkgsrc/devel/meson/patches/$missing" "$work/missing-export.log"
[ ! -e "$work/missing-export" ]
sh "$profile/tests/meson-selection.sh" "$work/meson-patched" "$work/meson-cli"
if command -v "${BMAKE:-bmake}" >/dev/null 2>&1; then
    sh "$profile/tests/python-selection.sh" "$work/pkgsrc" "$work/python-selection"
else
    echo 'SKIP: actual BSD make selection parsing; bmake unavailable, native gate required'
fi
sh "$profile/tests/llvm-source.sh" "$distfiles" "$work/llvm"
echo 'PASS: source checks; native packaging, ELF fixup and consumer runtime remain pending'
