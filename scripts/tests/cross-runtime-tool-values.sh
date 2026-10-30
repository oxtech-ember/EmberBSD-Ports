#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
# Cross builds must not record build-host tool paths in installed files:
# configure receives bare awk, grep, egrep and sed (libgcrypt-config, smistrip),
# and perl:run scripts whose #! names the build-host Perl name the target Perl
# after installation (aclocal, automake). Runs the exported make code on a
# scratch destdir; does not build a package.
# Usage: cross-runtime-tool-values.sh BMAKE PREPARED_PKGSRC
set -eu
[ "$#" -eq 2 ] || { echo "Usage: $0 BMAKE PREPARED_PKGSRC" >&2; exit 2; }
bmake=$1
tree=$(CDPATH= cd -- "$2" && pwd)
replace=$tree/mk/tools/replace.mk
fail() { echo "FAIL: $*" >&2; exit 1; }
scratch=$(mktemp -d "${TMPDIR:-/tmp}/cross-runtime-tools.XXXXXX")
trap 'rm -rf "$scratch"' EXIT INT TERM

# The configure tool values, evaluated by the exported conditional.
awk '/^\.if \$\{USE_CROSS_COMPILE:tl\} == "yes" && \$\{OPSYS\} != \$\{NATIVE_OPSYS\}$/ {p=1}
    p {print} p && /^\.endif$/ {exit}' "$replace" > "$scratch/values.mk"
grep -q 'TOOLS_VALUE_GNU.grep' "$scratch/values.mk" ||
    fail 'replace.mk has no cross configure tool values'
v() { "$bmake" -f "$scratch/values.mk" OPSYS=NetBSD NATIVE_OPSYS=Darwin "$@"; }
[ "$(v USE_CROSS_COMPILE=yes -V '${TOOLS_VALUE_GNU.grep}|${TOOLS_VALUE_GNU.egrep}|${TOOLS_VALUE_GNU.awk}|${TOOLS_VALUE_GNU.sed}')" = \
    'grep|grep -E|awk|sed' ] || fail 'cross configure receives build-host tool paths'
[ "$(v USE_CROSS_COMPILE=no -V '${TOOLS_VALUE_GNU.grep:U}${TOOLS_VALUE_GNU.awk:U}')" = '' ] ||
    fail 'native builds lost their tool command lines'
[ "$(v USE_CROSS_COMPILE=yes TOOLS_VALUE_GNU.grep=/pkg/grep -V '${TOOLS_VALUE_GNU.grep}')" = /pkg/grep ] ||
    fail 'a package can no longer select its grep'

# The perl:run shebang rewrite, run on a scratch destdir.
awk '/^ember-cross-perl-interpreter:/ {p=1} p {print} p && /^\tdone$/ {exit}' "$replace" > "$scratch/perl.mk"
grep -q '^	done$' "$scratch/perl.mk" || fail 'replace.mk has no perl interpreter rewrite'
grep -q '^post-install: ember-cross-perl-interpreter$' "$replace" ||
    fail 'the perl interpreter rewrite does not run after installation'
d=$scratch/destdir/usr/pkg
mkdir -p "$d/bin" "$d/share"
printf '#!/host/bin/perl\nprint "x";\n' > "$d/bin/plain"
printf '#!/host/bin/perl -w\nprint "y";\n' > "$d/bin/flags"
printf '#!/host/bin/perlx\n' > "$d/bin/other"
printf 'text #!/host/bin/perl\n' > "$d/share/doc"
printf '#!/host/bin/perl\n' > "$d/share/keep-mode"; chmod 755 "$d/share/keep-mode"
"$bmake" -f "$scratch/perl.mk" RUN= FIND=find SED=sed CAT=cat RM=rm \
    DESTDIR="$scratch/destdir" PREFIX=/usr/pkg TOOLS_PATH.perl=/host/bin/perl \
    PERL5=/usr/pkg/bin/perl ember-cross-perl-interpreter >/dev/null
[ "$(head -1 "$d/bin/plain")" = '#!/usr/pkg/bin/perl' ] || fail 'host Perl shebang kept'
[ "$(head -1 "$d/bin/flags")" = '#!/usr/pkg/bin/perl -w' ] || fail 'Perl shebang flags lost'
[ "$(sed -n 2p "$d/bin/plain")" = 'print "x";' ] || fail 'script body changed'
[ "$(head -1 "$d/bin/other")" = '#!/host/bin/perlx' ] || fail 'another interpreter rewritten'
[ "$(cat "$d/share/doc")" = 'text #!/host/bin/perl' ] || fail 'non-shebang text rewritten'
[ -x "$d/share/keep-mode" ] || fail 'rewrite dropped the file mode'
echo 'PASS: cross builds record target runtime tools, not build-host paths'
