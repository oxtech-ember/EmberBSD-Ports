#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). A selected Ports native toolset makes the
# exported mk/tools/tools.Darwin.mk skip its Xcode yacc and m4 lookups.
# Without a selection, the lookups and their results are unchanged.
# OSX_XCRUN is replaced by a stub that counts its calls and answers with
# fixed paths, so the test needs neither Xcode nor the Command Line Tools.
set -eu
[ "$#" -eq 3 ] || { echo 'Usage: darwin-native-toolset-xcode.sh EXPORTED_PKGSRC BMAKE NEW_WORK' >&2; exit 2; }
pkgsrc=$1 bmake=$2 out=$3
case "$pkgsrc$out" in *[!A-Za-z0-9_./-]*) echo 'Use simple paths.' >&2; exit 2;; esac
[ ! -e "$out" ] || { echo 'NEW_WORK must not exist' >&2; exit 2; }
mkdir "$out"
cat > "$out/xcrun" <<STUB
#!/bin/sh
echo "\$*" >> $out/calls
case "\$*" in
    *yacc*) echo /Library/Developer/CommandLineTools/usr/bin/yacc ;;
    *m4*) echo /Library/Developer/CommandLineTools/usr/bin/m4 ;;
esac
STUB
chmod +x "$out/xcrun"
cat > "$out/Makefile" <<MK
.include "$pkgsrc/mk/tools/tools.Darwin.mk"
all:
	@echo byacc=\${TOOLS_PLATFORM.byacc:U-}
	@echo yacc=\${TOOLS_PLATFORM.yacc:U-}
	@echo m4=\${TOOLS_PLATFORM.m4:U-}
	@echo noop=\${OSX_TOOLS_FORCE_NOOP:U-}
	@echo makeflags=\${MAKEFLAGS:MOSX_PATH_TO_*}
MK
run()
{
    : > "$out/calls"
    env -i PATH=/usr/bin:/bin "$bmake" -C "$out" -f Makefile OSX_XCRUN="$out/xcrun" "$@" all > "$out/vars"
    calls=$(($(wc -l < "$out/calls")))
}
fail()
{
    echo "FAIL: $*" >&2
    cat "$out/vars" >&2
    exit 1
}
# Default Darwin: Xcode supplies yacc and m4 as before.
run
[ "$calls" -gt 0 ] || fail 'the default Darwin parse no longer asks Xcode'
grep -qx 'byacc=/usr/bin/yacc' "$out/vars" || fail 'default byacc differs'
grep -qx 'yacc=/usr/bin/yacc' "$out/vars" || fail 'default yacc differs'
grep -qx 'm4=/usr/bin/m4' "$out/vars" || fail 'default m4 differs'
default_calls=$calls
# A selected native toolset: no Xcode lookup, no Xcode tool, no no-op tool.
run EMBERBSD_NATIVE_TOOLSET_MAKECONF=/absolute/host-tools.mk
[ "$calls" -eq 0 ] || fail "$calls Xcode lookups with a selected native toolset"
for line in byacc=- yacc=- m4=- noop=- makeflags=; do
    grep -qx "$line" "$out/vars" || fail "native toolset parse sets ${line%%=*}"
done
echo "PASS: $default_calls Xcode lookups by default, none with a selected native toolset"
