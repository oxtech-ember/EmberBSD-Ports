#!/bin/sh
# Exercise recipe integration without exporting another full pkgsrc tree.
set -eu
[ "$#" -le 1 ] || { echo "Usage: $0 [MPFR_4_2_2_ARCHIVE]" >&2; exit 2; }
root=$(CDPATH= cd -- "$(dirname -- "$0")/../../.." && pwd)
work=$(mktemp -d "${TMPDIR:-/tmp}/ember-gcc-profile.XXXXXXXX")
trap 'rm -rf "$work"' EXIT
trap 'exit 130' INT
trap 'exit 143' HUP TERM
expected=$(git -C "$root" ls-files --stage -- upstream/pkgsrc | awk '$1 == "160000" { print $2 }')
[ "$(git -C "$root/upstream/pkgsrc" rev-parse HEAD)" = "$expected" ]
git -C "$root/upstream/pkgsrc" archive -o "$work/base.tar" "$expected" \
    lang/gcc16 lang/gcc16-libs lang/gcc16-libjit math/mpfr math/mpcomplex devel/gmp devel/gtexinfo lang/tcl-expect mk/pkgformat/pkg/metadata.mk
tar -xf "$work/base.tar" -C "$work"
for delta in pkgsrc-gcc16.2.patch strict-tests.patch current-prerequisites.patch texinfo-gettext-order.patch stable-expect.patch gcc-tsvc-netbsd.patch gcc-modules-fallocate.patch gcc-netbsd-locale.patch gcc-netbsd-math.patch gcc-package-requires.patch gcc-netbsd-tls.patch gcc-cross-native.patch; do
    patch -f -E -d "$work" -p1 -F 0 < "$root/profiles/development-toolchain/patches/$delta"
done
grep -q '16.2.0' "$work/lang/gcc16/version.mk"
grep -q 'gcc-16.2.0.tar.xz' "$work/lang/gcc16/distinfo"
grep -qx 'DISTNAME=[[:space:]]*mpfr-4.2.2' "$work/math/mpfr/Makefile"
# Keep pkgsrc's NetBSD binary128 restriction and package layout unchanged.
grep -q -- '--disable-float128' "$work/math/mpfr/Makefile"
cmp "$root/upstream/pkgsrc/math/mpfr/PLIST" "$work/math/mpfr/PLIST"
cmp "$root/upstream/pkgsrc/math/mpfr/buildlink3.mk" "$work/math/mpfr/buildlink3.mk"
# Parse the actual GCC math option block and real buildlink files with BSD make.
# No full package configure/build or installed dependency mutation is involved.
if command -v "${BMAKE:-bmake}" >/dev/null 2>&1; then
    awk '/^\.if !empty\(PKG_OPTIONS:Mgcc-inplace-math\)/ {take=1}
        take {print} take && /^\.endif/ {exit}' "$work/lang/gcc16/options.mk" \
        > "$work/lang/gcc16/math-selection.mk"
    awk '/^BUILDLINK_API_DEPENDS.gmp/ || /^\.include .*gmp\/buildlink3.mk/' \
        "$work/math/mpfr/Makefile" > "$work/math/mpfr/bootstrap-selection.mk"
    cat > "$work/lang/gcc16/prerequisite-policy.mk" <<EOF_MAKE
.if \${WITH_PROFILE:Uyes} == "yes"
.include "$root/profiles/development-toolchain/mk.conf"
.endif
PKG_OPTIONS= gcc-c++
.if \${CONSUMER} == "gcc"
.include "$work/lang/gcc16/math-selection.mk"
.elif \${CONSUMER} == "mpc"
.include "$work/math/mpcomplex/buildlink3.mk"
.else
.include "$work/math/mpfr/bootstrap-selection.mk"
.endif
EOF_MAKE
    for consumer in gcc mpc; do
        "${BMAKE:-bmake}" -r -f "$work/lang/gcc16/prerequisite-policy.mk" \
            BSD_PKG_MK=yes CONSUMER="$consumer" -V BUILDLINK_API_DEPENDS.mpfr \
            > "$work/$consumer-policy.log"
        grep -Eq '(^| )mpfr>=4\.2\.2($| )' "$work/$consumer-policy.log"
    done
    "${BMAKE:-bmake}" -r -f "$work/lang/gcc16/prerequisite-policy.mk" \
        BSD_PKG_MK=yes CONSUMER=gcc WITH_PROFILE=no -V BUILDLINK_API_DEPENDS.mpfr \
        > "$work/unscoped-policy.log"
    ! grep -q 'mpfr>=4.2.2' "$work/unscoped-policy.log"
    "${BMAKE:-bmake}" -r -f "$work/lang/gcc16/prerequisite-policy.mk" \
        BSD_PKG_MK=yes CONSUMER=mpfr -V GCC_REQD -V BUILDLINK_TREE \
        > "$work/bootstrap-policy.log"
    [ -z "$(sed -n '1p' "$work/bootstrap-policy.log")" ]
    ! grep -Eq '(^| )mpfr($| )' "$work/bootstrap-policy.log"
    "${BMAKE:-bmake}" -r -f "$work/lang/gcc16/prerequisite-policy.mk" \
        CONSUMER=gcc -V BUILDLINK_API_DEPENDS.mpfr > "$work/outside-pkgsrc-policy.log"
    ! grep -q 'mpfr>=4.2.2' "$work/outside-pkgsrc-policy.log"
    echo 'PASS: BSD make GCC/MPC require current MPFR; unscoped and bootstrap boundaries'
else
    echo 'SKIP: BSD make prerequisite metadata; native policy check remains required'
fi
grep -q 'mpc-1.4.1' "$work/math/mpcomplex/Makefile"
grep -q 'texinfo-7.3' "$work/devel/gtexinfo/Makefile"
if command -v "${BMAKE:-bmake}" >/dev/null 2>&1; then
    ruby "$root/profiles/development-toolchain/tests/texinfo-iconv.rb" "$work/devel/gtexinfo" ${TEXINFO_PREPARED_SOURCE:+"$TEXINFO_PREPARED_SOURCE"}
fi
# Use pkgsrc's own verifier, not a second implementation of its RCS filtering.
# shasum/OpenSSL provide a portable adapter for pkgsrc's checksum verifier.
cat > "$work/digest" <<'EOF'
#!/bin/sh
algorithm=$1; shift
if [ "$algorithm" = SHA1 ]; then
    shasum -a 1 "$@" | awk '{ print $1 }'; exit
fi
for file do
    case "$algorithm" in
        SHA512) hash=$(shasum -a 512 "$file" | awk '{print $1}') ;;
        BLAKE2s) hash=$("${OPENSSL:-openssl}" dgst -blake2s256 "$file" | awk '{print $NF}') ;;
        *) exit 2 ;;
    esac
    printf '%s (%s) = %s\n' "$algorithm" "$file" "$hash"
done
EOF
chmod +x "$work/digest"
if [ "$#" = 1 ]; then
    archive=mpfr-4.2.2.tar.bz2
    expected_sha=$(awk -F '\t' '$1 == "mpfr" && $2 == "4.2.2" {print $4}' \
        "$root/profiles/development-toolchain/sources.tsv")
    [ -n "$expected_sha" ]
    [ "$(shasum -a 256 "$1" | awk '{print $1}')" = "$expected_sha" ]
    cp "$1" "$work/$archive"
    (cd "$work" && DIGEST="$work/digest" awk \
        -f "$root/upstream/pkgsrc/mk/checksum/checksum.awk" -- "math/mpfr/distinfo" "$archive")
    recorded=$(awk '$1 == "Size" {print $4}' "$work/math/mpfr/distinfo")
    [ "$(wc -c < "$work/$archive" | tr -d ' ')" = "$recorded" ]
    printf x >> "$work/$archive"
    if (cd "$work" && DIGEST="$work/digest" awk \
        -f "$root/upstream/pkgsrc/mk/checksum/checksum.awk" -- "math/mpfr/distinfo" "$archive") \
        > "$work/bad-archive.log" 2>&1; then
        echo 'pkgsrc unexpectedly accepted a corrupt MPFR archive.' >&2; exit 1
    fi
    echo 'PASS: MPFR SHA256/BLAKE2s/SHA512/size and corrupt archive rejection'
fi
for recipe in lang/gcc16 math/mpcomplex devel/gtexinfo lang/tcl-expect; do
    DIGEST="$work/digest" awk -f "$root/upstream/pkgsrc/mk/checksum/checksum.awk" \
        -- -p "$work/$recipe/distinfo" "$work/$recipe"/patches/patch-*
done
# Reproduce the review defect: an unfiltered patch hash must be rejected.
raw=$(shasum -a 1 "$work/devel/gtexinfo/patches/patch-configure" | awk '{ print $1 }')
sed "s/^SHA1 (patch-configure) = .*/SHA1 (patch-configure) = $raw/" \
    "$work/devel/gtexinfo/distinfo" > "$work/bad-distinfo"
if DIGEST="$work/digest" awk -f "$root/upstream/pkgsrc/mk/checksum/checksum.awk" \
    -- -p "$work/bad-distinfo" "$work/devel/gtexinfo/patches/patch-configure" \
    > "$work/bad-checksum.log" 2>&1; then
    echo 'pkgsrc unexpectedly accepted the unfiltered patch checksum.' >&2
    exit 1
fi
# These moved/new outputs caught a real 7.2-to-7.3 packaging regression.
for output in Texinfo/CommandsValues.pm Texinfo/ConfigXS.pm \
    Texinfo/Convert/IXIN.pm Texinfo/Convert/TreeElementReadDocBook.pm \
    XSTexinfo/Parsetexi.pm load_txi_modules; do
    grep -qx "share/texi2any/$output" "$work/devel/gtexinfo/PLIST"
done
for output in htmlxref.d/Texinfo_GNU.cnf htmlxref.d/Texinfo_nonGNU.cnf \
    info-hooks/gnu-manuals-locations.dat info-hooks/manual-not-found; do
    grep -qx "share/texinfo/$output" "$work/devel/gtexinfo/PLIST"
done
if grep -qx 'share/texinfo/htmlxref.cnf' "$work/devel/gtexinfo/PLIST"; then exit 1; fi
[ ! -e "$work/lang/gcc16/patches/patch-isl_configure" ]
if grep '^TEST_TARGET=' "$work/lang/gcc16/Makefile" | grep -q '||'; then exit 1; fi
if sh "$root/scripts/prepare-pkgsrc.sh" "$work/unknown" unknown; then exit 1; fi
[ ! -e "$work/unknown" ]
# A second application must fail instead of interactively reversing a patch.
if patch -f -E -d "$work" -p1 -F 0 < \
    "$root/profiles/development-toolchain/patches/current-prerequisites.patch" > "$work/repeat-prerequisites.log" 2>&1; then
    echo 'Repeated prerequisite patch unexpectedly succeeded.' >&2
    exit 1
fi
if patch -f -E -d "$work" -p1 -F 0 < \
    "$root/profiles/development-toolchain/patches/pkgsrc-gcc16.2.patch" > "$work/repeat.log" 2>&1; then
    echo 'Repeated patch unexpectedly succeeded.' >&2
    exit 1
fi
echo 'PASS: pinned profile, version/checksum update, no ISL patch, strict tests, repeat rejection'
