#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). A cross security/heimdal takes asn1_compile,
# slc and compile_et from the native heimdal-tools package, which installs
# only those programs and does not conflict with MIT Kerberos.
# Usage: cross-tools.sh HEIMDAL_TOOLS_PACKAGE.tgz
set -eu
pkg=${1:?usage: cross-tools.sh HEIMDAL_TOOLS_PACKAGE.tgz}
tree=$(CDPATH= cd -- "$(dirname -- "$0")/../../.." && pwd)
fail() { echo "FAIL: $*" >&2; exit 1; }

# The cross recipe depends on the tools package, not the full native Heimdal.
mk=$tree/security/heimdal/Makefile
grep -q '^TOOL_DEPENDS+= heimdal-tools>=7\.8\.0:\.\./\.\./security/heimdal-tools$' "$mk" ||
    fail 'cross heimdal does not depend on native heimdal-tools'
grep -q '^TOOL_DEPENDS+= heimdal-\[0-9\]' "$mk" &&
    fail 'cross heimdal still depends on the full native heimdal'
grep -q '^_EMBERBSD_HEIMDAL_TOOLS_DIR= ${TOOLBASE}/libexec/heimdal-tools$' "$mk" ||
    fail 'cross heimdal does not take its tools from libexec/heimdal-tools'
grep -q "^	for t in asn1_compile slc compile_et; do" "$mk" ||
    fail 'cross heimdal checks a different tool list'

work=$(mktemp -d "${TMPDIR:-/tmp}/heimdal-tools.XXXXXX")
trap 'rm -rf "$work"' EXIT
tar -xzf "$pkg" -C "$work"
# Only the three programs: no libraries, headers or other Kerberos files.
files=$(grep -v '^@' "$work/+CONTENTS" | grep -v '^+' | sort | tr '\n' ' ')
[ "$files" = 'libexec/heimdal-tools/asn1_compile libexec/heimdal-tools/compile_et libexec/heimdal-tools/slc ' ] ||
    fail "unexpected package contents: $files"
! grep -q '^@pkgcfl' "$work/+CONTENTS" || fail 'package has CONFLICTS'
! grep -q '^@pkgdep' "$work/+CONTENTS" || fail 'package has run-time dependencies'

# The programs run without Heimdal libraries in the tool prefix.
bin=$work/libexec/heimdal-tools
cd "$work"
printf 'error_table tst\nprefix TST\nerror_code ONE, "one"\nend\n' > tst.et
"$bin/compile_et" tst.et && grep -q TST_ONE tst.h || fail 'compile_et'
printf 'command = {\n\tname = "x"\n\thelp = "x"\n}\n' > cmds.in
"$bin/slc" cmds.in && grep -q x_wrap cmds.c || fail 'slc'
printf 'T DEFINITIONS ::= BEGIN\nN ::= INTEGER\nEND\n' > t.asn1
"$bin/asn1_compile" --one-code-file t.asn1 t && grep -q decode_N t.hx ||
    fail 'asn1_compile'
echo 'PASS: cross heimdal uses the native heimdal-tools generators'
