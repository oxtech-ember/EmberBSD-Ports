#!/bin/sh
# Check scripts/prepare-pkgsrc.sh with a small fixture repository.
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
work=$(mktemp -d "${TMPDIR:-/tmp}/ember-pkgsrc-test.XXXXXXXX")
trap 'rm -rf "$work"' EXIT
trap 'exit 130' INT
trap 'exit 143' HUP TERM
tab=$(printf '\t')
: "${PY:?Set an explicit Python}"
: "${EXPORT_TEST_GIT:?Set an explicit regression Git}"
: "${EXPORT_TEST_PATCH:?Set an explicit regression patch}"

mkdir "$work/existing" "$work/bin"
printf preserve > "$work/existing/sentinel"
if sh "$root/scripts/prepare-pkgsrc.sh" "$work/existing" 2>/dev/null; then exit 1; fi
[ "$(cat "$work/existing/sentinel")" = preserve ]
if sh "$root/scripts/prepare-pkgsrc.sh" relative-path 2>/dev/null; then exit 1; fi
if sh "$root/scripts/prepare-pkgsrc.sh" "$work/profile" development-toolchain 2>/dev/null; then exit 1; fi
[ ! -e "$work/profile" ]

# The fixture upstream tree.
upstream=$work/upstream
mkdir -p "$upstream/devel/alpha" "$upstream/devel/beta/patches" "$upstream/mk"
printf 'PKGNAME=alpha-1\n' > "$upstream/devel/alpha/Makefile"
printf 'PKGNAME=beta-1\n' > "$upstream/devel/beta/Makefile"
: > "$upstream/devel/beta/distinfo"
printf 'SUBDIR+=alpha\nSUBDIR+=beta\n' > "$upstream/devel/Makefile"
printf 'upstream\n' > "$upstream/mk/bsd.pkg.mk"

# The fixture repository.
fixture=$work/fixture
mkdir -p "$fixture/scripts" "$fixture/pkgsrc/devel/alpha" "$fixture/pkgsrc/devel/gamma" \
    "$fixture/pkgsrc/local-test/delta" "$fixture/profiles/test/recipes/devel/epsilon/patches" \
    "$fixture/profiles/test/patches" "$fixture/shared"
cp "$root/scripts/prepare-pkgsrc.sh" "$root/scripts/prepare-pkgsrc.py" "$fixture/scripts/"
printf 'PKGNAME=alpha-2\n' > "$fixture/pkgsrc/devel/alpha/Makefile"
printf 'PKGNAME=gamma-1\n' > "$fixture/pkgsrc/devel/gamma/Makefile"
printf 'SUBDIR+=delta\n' > "$fixture/pkgsrc/local-test/Makefile"
printf 'PKGNAME=delta-1\n' > "$fixture/pkgsrc/local-test/delta/Makefile"
printf 'PKGNAME=epsilon-1\n' > "$fixture/profiles/test/recipes/devel/epsilon/Makefile"
printf -- '--- a/x.c\n+++ b/x.c\n@@ -1 +1 @@\n-old\n+new\n' > "$fixture/shared/patch-x.c"
ln -s ../../../../../../shared/patch-x.c \
    "$fixture/profiles/test/recipes/devel/epsilon/patches/patch-x.c"
sum=$(shasum -a 1 "$fixture/shared/patch-x.c" | awk '{ print $1 }')
printf 'SHA1 (patch-x.c) = %s\n' "$sum" > "$fixture/profiles/test/recipes/devel/epsilon/distinfo"
printf '# Replaced recipes.\ndevel/alpha\n' > "$fixture/pkgsrc/replaces"
cat > "$fixture/profiles/test/patches/mk.patch" <<'PATCH'
--- a/mk/bsd.pkg.mk
+++ b/mk/bsd.pkg.mk
@@ -1 +1,2 @@
 upstream
+ember
PATCH
cat > "$fixture/profiles/test/patches/new-file.patch" <<'PATCH'
diff --git a/mk/new.mk b/mk/new.mk
new file mode 100644
--- /dev/null
+++ b/mk/new.mk
@@ -0,0 +1 @@
+new
PATCH
printf 'new-file.patch\t%s\n' "$(shasum -a 256 "$fixture/profiles/test/patches/new-file.patch" | awk '{ print $1 }')" \
    > "$fixture/profiles/test/sources.tsv"
printf 'CHECK=yes\n' > "$fixture/profiles/test/mk.conf"
cat > "$fixture/pkgsrc/export.conf" <<CONF
# Fixture export.
recipe${tab}profiles/test/recipes/devel/epsilon${tab}devel/epsilon
patch${tab}profiles/test/patches/mk.patch
git-apply${tab}profiles/test/patches/new-file.patch${tab}profiles/test/sources.tsv
recipe-patch${tab}shared/patch-x.c${tab}devel/beta${tab}patch-y.c
file${tab}profiles/test/mk.conf${tab}EMBERBSD-TEST-MK.CONF
CONF
cp -R "$fixture" "$work/clean"

run() {
    FAKE_MATCH=1 FAKE_ARCHIVE="$upstream" \
        "$PY" -B "$root/scripts/tests/export-fixture.py" "$fixture" "$1"
}
reject() {
    if run "$work/$1" > "$work/$1.log" 2>&1; then
        echo "FAIL: the export accepted $1" >&2; exit 1
    fi
    grep -F "$2" "$work/$1.log" >/dev/null || { cat "$work/$1.log" >&2; exit 1; }
}
restore() {
    rm -rf "$fixture"
    cp -R "$work/clean" "$fixture"
}

if FAKE_ARCHIVE="$upstream" "$PY" -B "$root/scripts/tests/export-fixture.py" "$fixture" "$work/mismatch" 2>/dev/null; then exit 1; fi
[ ! -e "$work/mismatch" ]

run "$work/export" > "$work/export.log"
export=$work/export
grep -Fx 'PKGNAME=alpha-2' "$export/devel/alpha/Makefile" >/dev/null
grep -Fx 'PKGNAME=gamma-1' "$export/devel/gamma/Makefile" >/dev/null
grep -Fx 'SUBDIR+=delta' "$export/local-test/Makefile" >/dev/null
[ -f "$export/local-test/delta/Makefile" ]
[ -f "$export/devel/epsilon/patches/patch-x.c" ] && [ ! -L "$export/devel/epsilon/patches/patch-x.c" ]
grep -Fx 'ember' "$export/mk/bsd.pkg.mk" >/dev/null
grep -Fx 'new' "$export/mk/new.mk" >/dev/null
cmp "$fixture/shared/patch-x.c" "$export/devel/beta/patches/patch-y.c"
grep -Fx "SHA1 (patch-y.c) = $sum" "$export/devel/beta/distinfo" >/dev/null
cmp "$fixture/profiles/test/mk.conf" "$export/EMBERBSD-TEST-MK.CONF"
grep -Fx 1111111111111111111111111111111111111111 "$export/EMBERBSD-PKGSRC-REVISION" >/dev/null
[ ! -e "$export/EMBERBSD-PKGSRC-CONFIG" ]

# An upstream recipe path needs a pkgsrc/replaces entry.
grep -v '^devel/alpha$' "$work/clean/pkgsrc/replaces" > "$fixture/pkgsrc/replaces"
reject missing-replaces 'Upstream already has devel/alpha'
restore
printf 'devel/zeta\n' >> "$fixture/pkgsrc/replaces"
reject stale-replaces 'pkgsrc/replaces names devel/zeta'
restore
# Two sources for one recipe path.
printf 'recipe\tprofiles/test/recipes/devel/epsilon\tdevel/gamma\n' >> "$fixture/pkgsrc/export.conf"
reject duplicate 'Two recipe sources provide devel/gamma'
restore
# Recipe completeness.
rm "$fixture/pkgsrc/devel/gamma/Makefile"
reject no-makefile 'pkgsrc/devel/gamma has no Makefile'
restore
printf 'other\n' > "$fixture/profiles/test/recipes/devel/epsilon/patches/patch-z.c"
reject undeclared 'Undeclared patch: profiles/test/recipes/devel/epsilon/patches/patch-z.c'
restore
printf '+changed\n' >> "$fixture/shared/patch-x.c"
reject checksum 'Patch checksum differs: profiles/test/recipes/devel/epsilon/patches/patch-x.c'
restore
ln -s ../../../../upstream/mk/bsd.pkg.mk "$fixture/pkgsrc/devel/gamma/outside"
reject outside-link 'Link leaves the repository'
restore
ln -s "$work/upstream/mk/bsd.pkg.mk" "$fixture/pkgsrc/devel/gamma/absolute"
reject absolute-link 'Link leaves the repository'
restore
# Each infrastructure patch applies once.
printf 'patch\tprofiles/test/patches/mk.patch\n' >> "$fixture/pkgsrc/export.conf"
reject twice 'Infrastructure patch does not apply: profiles/test/patches/mk.patch'
restore
printf 'changed\n' >> "$fixture/profiles/test/patches/new-file.patch"
reject manifest 'Infrastructure patch differs from'
grep -F 'profiles/test/sources.tsv' "$work/manifest.log" >/dev/null
restore
printf 'profile\tshared/patch-x.c\n' >> "$fixture/pkgsrc/export.conf"
reject method 'unknown method profile'
restore
# A new overlay category must not exist upstream.
mkdir "$upstream/local-test"
printf upstream > "$upstream/local-test/sentinel"
reject collision 'Upstream already has local-test'
[ "$(cat "$work/collision/local-test/sentinel")" = upstream ]
echo 'PASS: path, revision and argument rejection; overlay, recipe, patch and file export; replaces, duplicate, completeness, link, repeated patch and collision rejection'
