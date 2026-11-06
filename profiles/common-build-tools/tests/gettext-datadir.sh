#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted).
# bmake must parse the host msgfmt data-directory fragment. The selected
# prefix is the logical path named by the executable: a symlink of the
# executable is not followed, and a symlink of its directory or parents is
# not replaced by the producer. Spaces stay one path. GNU msgfmt then
# appends its own version suffix under that directory.
# Usage: gettext-datadir.sh NEW_OUTPUT
set -eu
[ "$#" = 1 ] || { echo 'Usage: gettext-datadir.sh NEW_OUTPUT' >&2; exit 2; }
out=$1
case "$out" in /*) ;; *) echo 'NEW_OUTPUT must be absolute' >&2; exit 2 ;; esac
[ ! -e "$out" ] || exit 2
ports=$(CDPATH= cd -- "$(dirname -- "$0")/../../.." && pwd)
mkdir -p "$out"
fail() { echo "FAIL: $*" >&2; exit 1; }
bmake=${BMAKE:-bmake}
msgfmt=${MSGFMT:-msgfmt}
command -v "$bmake" >/dev/null 2>&1 || fail "bmake is required ($bmake)"
command -v "$msgfmt" >/dev/null 2>&1 || fail "GNU msgfmt is required ($msgfmt)"
patch=$ports/profiles/common-build-tools/patches/pkgsrc-gettext-datadir.patch
[ -f "$patch" ] || fail 'host data-directory patch is missing'
grep -q 'pwd -L' "$patch" || fail 'patch does not keep the logical selected directory'
grep -q '$${bindir%/\*}' "$patch" || fail 'patch still splits the prefix in make'
grep -q 'GETTEXTDATADIR=${GETTEXTDATADIR:Q}' "$patch" ||
    fail 'patch does not shell-quote the data directory'
if grep -q ':H}/share/gettext' "$patch"; then
    fail 'patch still applies :H to each word'
fi
grep -q 'devel/gettext-tools' "$patch" || fail 'patch does not record the gettext-tools skip'
grep -q -- '--enable-relocatable' \
    "$ports/profiles/common-build-tools/patches/gettext-external-recipe.patch" ||
    fail 'gettext-tools is not built relocatable'
revision=$(sed -n 's/^+PKGREVISION= \([0-9][0-9]*\)$/\1/p' \
    "$ports/profiles/common-build-tools/patches/pkgsrc-gettext-external-tree-sitter.patch")
[ "$revision" = 9 ] || fail "Darwin gettext-tools revision is ${revision:-missing}, expected 9"
identity=gettext-tools-1.0nb$revision
for file in \
    "$ports/profiles/common-build-tools/tests/gettext-bootstrap-options.py" \
    "$ports/profiles/common-build-tools/tests/gettext-native-lifecycle.py" \
    "$ports/profiles/development-toolchain/darwin-bootstrap.md"
do
    grep -q "$identity" "$file" || fail "$file does not require $identity"
    if grep -q 'gettext-tools-1.0nb7' "$file"; then
        fail "$file still requires nb7"
    fi
done
awk '/^\+\+\+/ {next} /^\+/ {sub(/^\+/, ""); print}' "$patch" > "$out/fragment.mk"
cat "$out/fragment.mk" > "$out/Makefile"
cat >> "$out/Makefile" << 'EOF'
show-make:
	@env ${MAKE_ENV} /bin/sh -c 'printf "make-child=%s\n" "$$GETTEXTDATADIR"'
show-configure:
	@env ${CONFIGURE_ENV} /bin/sh -c 'printf "configure-child=%s\n" "$$GETTEXTDATADIR"'
show-all:
	@env ${ALL_ENV} /bin/sh -c 'printf "all-child=%s\n" "$$GETTEXTDATADIR"'
EOF
phase() {
    tool=$1 target=$2
    "$bmake" -f "$out/Makefile" EMBERBSD_BUILD_MSGFMT="$tool" "$target"
}
expect_phases() {
    tool=$1 expected=$2
    for target in show-make show-configure show-all; do
        got=$(phase "$tool" "$target" | sed -n "s/^${target#show-}-child=//p")
        [ "$got" = "$expected" ] || fail "$target for $tool became [$got] expected [$expected]"
    done
}
mkdir -p "$out/producer/bin" "$out/file/selected/bin" "$out/prefix/producer/bin" \
    "$out/binlink/producer/bin" "$out/binlink/selected" "$out/spacey dir/bin" \
    "$out/po"
printf '#!/bin/sh\nexit 0\n' > "$out/producer/bin/msgfmt"
chmod +x "$out/producer/bin/msgfmt"
cp "$out/producer/bin/msgfmt" "$out/prefix/producer/bin/msgfmt"
cp "$out/producer/bin/msgfmt" "$out/binlink/producer/bin/msgfmt"
ln -s "$out/producer/bin/msgfmt" "$out/file/selected/bin/msgfmt"
ln -s "$out/prefix/producer" "$out/prefix/selected"
ln -s "$out/binlink/producer/bin" "$out/binlink/selected/bin"
ln -s "$(command -v "$msgfmt")" "$out/spacey dir/bin/msgfmt"
expect_phases "$out/file/selected/bin/msgfmt" "$out/file/selected/share/gettext"
expect_phases "$out/prefix/selected/bin/msgfmt" "$out/prefix/selected/share/gettext"
expect_phases "$out/binlink/selected/bin/msgfmt" "$out/binlink/selected/share/gettext"
case "$(phase "$out/prefix/selected/bin/msgfmt" show-make | sed -n 's/^make-child=//p')" in
    "$out/prefix/producer"/*) fail 'directory symlink was replaced by the producer' ;;
esac
case "$(phase "$out/file/selected/bin/msgfmt" show-make | sed -n 's/^make-child=//p')" in
    "$out/producer"/*) fail 'file symlink was followed to the producer' ;;
esac
expect_phases "$out/spacey dir/bin/msgfmt" "$out/spacey dir/share/gettext"
space_data=$(phase "$out/spacey dir/bin/msgfmt" show-make | sed -n 's/^make-child=//p')
explicit="$out/explicit dir/share/gettext"
got=$(env GETTEXTDATADIR="$explicit" "$bmake" -f "$out/Makefile" \
    EMBERBSD_BUILD_MSGFMT="$out/spacey dir/bin/msgfmt" show-make |
    sed -n 's/^make-child=//p')
[ "$got" = "$explicit" ] || fail "explicit data directory became [$got]"
version=$("$msgfmt" --version | awk '/GNU gettext-tools/ {print $NF; exit}')
[ -n "$version" ] || fail 'msgfmt did not report a GNU version'
mkdir -p "$out/spacey dir/share/gettext/its" "$out/spacey dir/share/gettext-$version/its"
cat > "$out/spacey dir/share/gettext/its/other.loc" << 'EOF'
<?xml version="1.0"?>
<locatingRules>
  <locatingRule name="other" pattern="*.gschema.xml">
    <documentRule localName="schemalist" target="missing.its"/>
  </locatingRule>
</locatingRules>
EOF
cat > "$out/spacey dir/share/gettext-$version/its/ember-metainfo.its" << 'EOF'
<?xml version="1.0"?>
<its:rules xmlns:its="http://www.w3.org/2005/11/its" version="2.0">
  <its:translateRule selector="/component" translate="no"/>
  <its:translateRule selector="/component/summary" translate="yes"/>
</its:rules>
EOF
cat > "$out/spacey dir/share/gettext-$version/its/ember-metainfo.loc" << 'EOF'
<?xml version="1.0"?>
<locatingRules>
  <locatingRule name="ember" pattern="*.ember-metainfo.xml">
    <documentRule localName="component" target="ember-metainfo.its"/>
  </locatingRule>
</locatingRules>
EOF
cat > "$out/app.ember-metainfo.xml" << 'EOF'
<?xml version="1.0"?>
<component>
  <summary>Hello</summary>
</component>
EOF
run_msgfmt() {
    env GETTEXTDATADIR="$1" "$msgfmt" --xml -d "$out/po" \
        --template "$out/app.ember-metainfo.xml" -o "$out/out.xml" >"$out/msgfmt.out" 2>"$out/msgfmt.err"
}
if run_msgfmt "$space_data"; then
    if grep -q 'cannot locate ITS rules' "$out/msgfmt.err"; then
        fail 'versioned rules were not used'
    fi
    [ -s "$out/out.xml" ] || fail 'msgfmt wrote no XML'
else
    fail "msgfmt rejected the selected prefix: $(cat "$out/msgfmt.err")"
fi
rm -rf "$out/spacey dir/share/gettext-$version"
if run_msgfmt "$space_data"; then
    fail 'unversioned its/ alone satisfied a versioned rule'
fi
grep -q 'cannot locate ITS rules' "$out/msgfmt.err" ||
    fail "missing versioned rules did not report ITS failure: $(cat "$out/msgfmt.err")"
echo 'PASS: bmake keeps a spaced logical prefix and msgfmt uses its version suffix'
