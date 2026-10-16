#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Reject a host-tool fallback and exercise exported target tools in a child shell.
set -eu
here=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd -P)
[ -f "$here/target-tools.sh" ] || { echo 'FAIL: explicit target-binutils selection is missing' >&2; exit 1; }
work=$(mktemp -d /tmp/ember-gcc-runtime-binutils.XXXXXX)
trap 'rm -rf "$work"' EXIT HUP INT TERM
mkdir -p "$work/kernel/bin" "$work/host"
cat > "$work/tool" <<'EOF'
#!/bin/sh
case "$1" in
    --version)
        name=${0##*-}; [ "$name" != as ] || name=assembler
        echo "GNU $name (NetBSD Binutils nb1) 2.42"
        [ "$name" != assembler ] || echo "This assembler was configured for a target of x86_64--netbsd";;
    *) exit 99;;
esac
EOF
chmod +x "$work/tool"
for tool in ar as ld nm objcopy objdump ranlib readelf strip; do
    cp "$work/tool" "$work/kernel/bin/x86_64--netbsd-$tool"
done
cat > "$work/host/nm" <<'EOF'
#!/bin/sh
echo 'FAIL: Darwin nm was invoked' >&2
exit 98
EOF
chmod +x "$work/host/nm"
export PATH=$work/host:$PATH
kernel=$work/kernel triplet=x86_64--netbsd
export kernel triplet
fail() { echo "$*" >&2; exit 2; }
. "$here/target-tools.sh"
export EXPECTED_TOOLS=$work/kernel/bin
sh -eu -c '
    [ "$AR_FOR_TARGET" = "$EXPECTED_TOOLS/x86_64--netbsd-ar" ]
    [ "$NM_FOR_TARGET" = "$EXPECTED_TOOLS/x86_64--netbsd-nm" ]
    [ "$RANLIB_FOR_TARGET" = "$EXPECTED_TOOLS/x86_64--netbsd-ranlib" ]
    [ "$READELF_FOR_TARGET" = "$EXPECTED_TOOLS/x86_64--netbsd-readelf" ]
    [ "$(command -v x86_64--netbsd-ar)" = "$AR_FOR_TARGET" ]
    "$NM_FOR_TARGET" --version | grep -q "^GNU nm "
'
cp "$work/host/nm" "$work/kernel/bin/x86_64--netbsd-nm"
if (. "$here/target-tools.sh") > "$work/reject.log" 2>&1; then
    echo 'FAIL: non-GNU target nm accepted' >&2; exit 1
fi
printf '#!/bin/sh\necho "GNU ar (wrong tool)"\n' > "$work/kernel/bin/x86_64--netbsd-nm"
if (. "$here/target-tools.sh") > "$work/reject.log" 2>&1; then
    echo 'FAIL: wrong GNU tool accepted as nm' >&2; exit 1
fi
cp "$work/tool" "$work/kernel/bin/x86_64--netbsd-nm"
printf '#!/bin/sh\necho "GNU assembler 2.42"\necho "This assembler was configured for a target of aarch64--netbsd"\n' > "$work/kernel/bin/x86_64--netbsd-as"
if (. "$here/target-tools.sh") > "$work/reject.log" 2>&1; then
    echo 'FAIL: foreign GNU assembler target accepted' >&2; exit 1
fi
echo 'PASS: absolute exported GNU target binutils and PATH, without host nm fallback'
