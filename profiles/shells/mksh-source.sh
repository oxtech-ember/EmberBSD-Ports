#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Compare the mksh source copy with the archive.
set -eu
[ "$#" = 1 ] || { echo 'Usage: mksh-source.sh /absolute/mksh-R59c.tgz' >&2; exit 2; }
archive=$1
digest=77ae1665a337f1c48c61d6b961db3e52119b38e58884d1c89684af31f87bc506
profile=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
files=$profile/../../pkgsrc/shells/mksh/files
actual=$(shasum -a 256 "$archive" | awk '{ print $1 }')
[ "$actual" = "$digest" ] || { echo "Unexpected archive SHA256: $actual" >&2; exit 1; }
work=$(mktemp -d "${TMPDIR:-/tmp}/ember-mksh-source.XXXXXXXX")
trap 'rm -rf "$work"' EXIT HUP INT TERM
tar -xzf "$archive" -C "$work"
# The binary OS/2 icon is the only archive file that is not in the copy.
rm "$work/mksh/mksh.ico"
diff -r "$work/mksh" "$files"
echo 'PASS: shells/mksh/files matches mksh-R59c.tgz, without mksh.ico'
