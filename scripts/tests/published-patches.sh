#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Reproduce a working-tree-only patch hidden by a user's global ignore pattern.
set -eu
[ "$#" -eq 1 ] || { echo "Usage: $0 NEW_WORK" >&2; exit 2; }
root=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
mkdir "$1"
work=$(CDPATH= cd -- "$1" && pwd)
fixture=$work/repository
mkdir "$fixture"
git init -q "$fixture"
printf '*.build\nMakefile\n' > "$work/global-excludes"
git -C "$fixture" config core.excludesFile "$work/global-excludes"
recipe=profiles/common-media/recipes/audio/example
mkdir -p "$fixture/$recipe/patches"
printf 'retained patch payload\n' > "$fixture/$recipe/patches/patch-meson.build"
sha=$(shasum -a 1 "$fixture/$recipe/patches/patch-meson.build" | awk '{print $1}')
printf 'SHA1 (patch-meson.build) = %s\n' "$sha" > "$fixture/$recipe/distinfo"
git -C "$fixture" add "$recipe/distinfo"
git -C "$fixture" check-ignore "$recipe/patches/patch-meson.build" > "$work/ignored-before.log"
if sh "$root/scripts/check-published-patches.sh" "$fixture" > "$work/untracked.log" 2>&1; then exit 1; fi
grep -F 'Declared patch is not tracked by Git:' "$work/untracked.log" >/dev/null
cp "$root/.gitignore" "$fixture/.gitignore"
if git -C "$fixture" check-ignore "$recipe/patches/patch-meson.build"; then exit 1; fi
firmware_recipe=profiles/development-toolchain/recipes/devel/gmake
mkdir -p "$fixture/$firmware_recipe"
printf 'DISTNAME=make-4.4.1\n' > "$fixture/$firmware_recipe/Makefile"
if git -C "$fixture" check-ignore "$firmware_recipe/Makefile"; then exit 1; fi
# Normal add must work. A forced add would hide a broken repository ignore policy.
git -C "$fixture" add .gitignore "$recipe/patches/patch-meson.build" "$firmware_recipe/Makefile"
sh "$root/scripts/check-published-patches.sh" "$fixture"
printf 'ordinary build output\n' > "$fixture/output.build"
mkdir -p "$fixture/work/patches"
printf 'ignored work output\n' > "$fixture/work/patches/patch-output.build"
git -C "$fixture" check-ignore output.build work/patches/patch-output.build > "$work/ignored-outputs.log"
[ "$(wc -l < "$work/ignored-outputs.log" | tr -d ' ')" = 2 ]
# Archive the index as a tree without creating a commit or changing user identity.
tree=$(git -C "$fixture" write-tree)
git -C "$fixture" archive --format=tar --output="$work/published.tar" "$tree"
mkdir "$work/published"
tar -xf "$work/published.tar" -C "$work/published"
cmp "$fixture/$recipe/patches/patch-meson.build" "$work/published/$recipe/patches/patch-meson.build"
cmp "$fixture/$firmware_recipe/Makefile" "$work/published/$firmware_recipe/Makefile"
rm "$fixture/$recipe/patches/patch-meson.build"
if sh "$root/scripts/check-published-patches.sh" "$fixture" > "$work/missing.log" 2>&1; then exit 1; fi
grep -F 'Missing declared patch:' "$work/missing.log" >/dev/null
echo 'PASS: ignored/untracked and missing patches fail; normal add and clean archive retain patches; build outputs stay ignored'
