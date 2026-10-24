#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD; AI-assisted regression for the real CF_INSTALL_MAN output.
# This check emits the production configure heredoc. It runs no compiler.
set -eu
[ "$#" -eq 2 ] || { echo "Usage: $0 BYACC_SOURCE NEW_WORK" >&2; exit 2; }
source=$1
mkdir "$2"
work=$(CDPATH= cd -- "$2" && pwd)
shell=${TEST_SHELL:-/bin/sh}
real_mktemp=$(command -v mktemp)
real_cp=$(command -v cp)
real_gzip=$(command -v gzip)
mkdir "$work/tools" "$work/default-tmp" "$work/selected temporary"
awk '
$0 == "cat >$cf_install_man <<\"CF_EOF\"" { take=1 }
take { print }
take && $0 == "CF_EOF" { exit }
' "$source/configure" > "$work/emit.sh"
cf_install_man="$work/install-man.in" "$shell" "$work/emit.sh"
test -s "$work/install-man.in"

cat > "$work/tools/mktemp" <<'SH'
#!/bin/sh
[ "$TEST_FAILURE" != mktemp ] || exit 17
[ "$TEST_FAILURE" != empty ] || exit 0
[ "$1" = -d ] || exit 91
shift
if [ "$#" = 0 ]; then
    # Model Darwin's default directory without writing outside the fixture.
    template="$TEST_WORK/default-tmp/install-man.XXXXXXXXXX"
else
    [ "$#" = 1 ] || exit 92
    template=$1
fi
created=$("$REAL_MKTEMP" -d "$template") || exit $?
printf '%s\n' "$created" > "$TEST_TMP_RECORD"
printf '%s\n' "$created"
SH
cat > "$work/tools/cp" <<'SH'
#!/bin/sh
[ "$TEST_FAILURE" != copy ] || exit 23
# A failing legacy mktemp must never cause a real write to /yacc.1.
case "$2" in "$TEST_WORK"/*) ;; *) exit 97 ;; esac
exec "$REAL_CP" "$@"
SH
cat > "$work/tools/install-data" <<'SH'
#!/bin/sh
printf '%s\n' "$*" > "$TEST_INSTALL_RECORD"
[ "$TEST_FAILURE" != install ] || exit 31
exec "$REAL_CP" "$@"
SH
chmod +x "$work/tools/mktemp" "$work/tools/cp" "$work/tools/install-data"

installer() {
    transform=$1 compress=$2 suffix=$3 output=$4
    sed -e "s%@INSTALL@%$work/tools/install-data%g" \
        -e "s%@INSTALL_DATA@%$work/tools/install-data%g" \
        -e "s%@program_transform_name@%$transform%g" \
        -e "s%@cf_manpage_so_strip@%$suffix%g" \
        -e "s%@cf_manpage_compress@%$compress%g" \
        -e 's%@cf_manpage_coptions@%-n%g' \
        -e 's%@LN_S@%ln -s%g' "$work/install-man.in" > "$output"
}
installer 's,x,x,' '' '' "$work/normal.sh"
installer 's,yacc,byacc,' '' '' "$work/renamed.sh"
installer 's,yacc,byacc,' "$real_gzip" gz "$work/compressed.sh"
cat > "$work/yacc.1" <<'MAN'
.TH YACC 1
.ds N Yacc
.ds n yacc
.SH NAME
\*n \- parser generator
MAN

failures=0
check() {
    label=$1
    shift
    if "$@"; then echo "PASS: $label"; else
        echo "FAIL: $label" >&2
        failures=$((failures + 1))
    fi
}
run() {
    name=$1 mode=$2 program=$3
    shift 3
    mkdir "$work/$name"
    if env PATH="$work/tools:$PATH" TMPDIR="$work/selected temporary" \
        TEST_WORK="$work" TEST_FAILURE="$mode" REAL_MKTEMP="$real_mktemp" \
        REAL_CP="$real_cp" TEST_TMP_RECORD="$work/$name/tmpdir" \
        TEST_INSTALL_RECORD="$work/$name/install-call" \
        "$shell" "$program" "$@" > "$work/$name/log" 2>&1; then
        status=0
    else
        status=$?
    fi
}

run normal none "$work/normal.sh" "$work/yacc.1" "$work/normal/yacc.1"
check 'normal manual install succeeds' test "$status" = 0
check 'normal manual bytes are preserved' cmp -s "$work/yacc.1" "$work/normal/yacc.1"
created=$(cat "$work/normal/tmpdir")
case "$created" in "$work/selected temporary"/*) selected=yes ;; *) selected=no ;; esac
check 'explicit TMPDIR owns the temporary directory' test "$selected" = yes
check 'successful install removes its temporary directory' test ! -d "$created"

for mode in mktemp empty copy install; do
    run "$mode" "$mode" "$work/normal.sh" "$work/yacc.1" "$work/$mode/yacc.1"
    case "$mode" in mktemp) expected=17 ;; empty) expected=1 ;; copy) expected=23 ;; install) expected=31 ;; esac
    check "$mode failure preserves its nonzero status" test "$status" = "$expected"
    check "$mode failure does not install a manual" test ! -f "$work/$mode/yacc.1"
    if test -f "$work/$mode/tmpdir"; then
        created=$(cat "$work/$mode/tmpdir")
        check "$mode failure removes its temporary directory" test ! -d "$created"
    fi
done

run plain-renamed none "$work/renamed.sh" "$work/yacc.1" "$work/plain-renamed/byacc.1"
check 'uncompressed transformed manual installs' test "$status" = 0
check 'uncompressed manual keeps the transformed heading' grep -q '^.TH BYACC 1$' "$work/plain-renamed/byacc.1"
check 'uncompressed manual keeps the transformed name string' grep -q '^.ds n byacc$' "$work/plain-renamed/byacc.1"

run directory-normal none "$work/renamed.sh" "$work/yacc.1" "$work/directory-normal"
check 'directory operand accepts an absolute uncompressed input' test "$status" = 0
check 'directory operand uses the manual basename' test -f "$work/directory-normal/yacc.1"
if test -f "$work/directory-normal/yacc.1"; then
    check 'directory manual keeps its transformed heading' grep -q '^.TH BYACC 1$' "$work/directory-normal/yacc.1"
fi

run directory-compressed none "$work/compressed.sh" "$work/yacc.1" "$work/directory-compressed"
check 'directory operand accepts an absolute compressed input' test "$status" = 0
check 'directory operand keeps the compressed manual basename' test -f "$work/directory-compressed/yacc.1.gz"
if test -f "$work/directory-compressed/yacc.1.gz"; then
    "$real_gzip" -dc "$work/directory-compressed/yacc.1.gz" > "$work/directory-compressed/manual.txt"
    check 'compressed directory manual keeps its transformed heading' grep -q '^.TH BYACC 1$' "$work/directory-compressed/manual.txt"
fi

run transformed none "$work/compressed.sh" "$work/yacc.1" "$work/transformed/byacc.1"
check 'compressed transformed manual installs' test "$status" = 0
"$real_gzip" -dc "$work/transformed/byacc.1.gz" > "$work/transformed/manual.txt"
check 'manual heading retains the upstream name transform' grep -q '^.TH BYACC 1$' "$work/transformed/manual.txt"
check 'manual string retains the upstream name transform' grep -q '^.ds n byacc$' "$work/transformed/manual.txt"

run linked none "$work/normal.sh" -l alias.1 "$work/normal/yacc.1"
check 'manual alias creation succeeds' test "$status" = 0
check 'manual alias points to the installed page' test -L "$work/normal/alias.1"
check 'manual alias retains its content' cmp -s "$work/normal/yacc.1" "$work/normal/alias.1"
run duplicate none "$work/normal.sh" -l alias.1 "$work/normal/yacc.1"
check 'duplicate alias failure is not masked by cleanup' test "$status" != 0
run removed none "$work/normal.sh" "$work/normal/alias.1"
check 'manual alias removal succeeds' test "$status" = 0
check 'manual alias removal keeps the original' test -f "$work/normal/yacc.1"
check 'manual alias was removed' test ! -e "$work/normal/alias.1"

[ "$failures" = 0 ] || { echo "$failures installer checks failed" >&2; exit 1; }
echo 'All CF_INSTALL_MAN shell checks passed; no C compilation ran.'
