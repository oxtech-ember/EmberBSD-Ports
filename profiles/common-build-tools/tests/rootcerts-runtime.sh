#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Run only in an owned temporary target prefix.
set -eu
[ "$#" -eq 4 ] || [ "$#" -eq 5 ] || {
    echo 'Usage: rootcerts-runtime.sh STAGED_PREFIX NEW_WORK SCRIPT_SHA256 CERTDATA_SHA256 [VERIFIED_BASE_TOOLS_PREFIX]' >&2
    exit 2
}
case "$1:$2" in /*:/*) ;; *) echo 'Absolute paths required' >&2; exit 2 ;; esac
[ -d "$1" ] && [ ! -e "$2" ] && [ ! -L "$2" ]
prefix=$(CDPATH= cd -- "$1" && pwd -P)
script=$prefix/sbin/mozilla-rootcerts
data=$prefix/share/mozilla-rootcerts/certdata.txt
[ "$(uname -s)" = NetBSD ]
[ "$(sha256 -q "$script")" = "$3" ]
[ "$(sha256 -q "$data")" = "$4" ]
mkdir -m 700 "$2"
work=$(CDPATH= cd -- "$2" && pwd -P)
case "$prefix/" in "$work/"*) echo 'Stage and work overlap' >&2; exit 2 ;; esac
case "$work/" in "$prefix/"*) echo 'Stage and work overlap' >&2; exit 2 ;; esac
uname -a > "$work/uname.txt"
extra=${5:-}
if [ -n "$extra" ]; then
    case "$extra" in /*) ;; *) echo 'Absolute tools prefix required' >&2; exit 2 ;; esac
    extra=$(CDPATH= cd -- "$extra" && pwd -P)
    echo_tool=$extra/bin/echo
    expr_tool=$extra/bin/expr
    ln_tool=$extra/bin/ln
    openssl_tool=$extra/bin/openssl
    printf '%s\n' 'Explicit environment API check; default full-base tools are not assessed.' \
        > "$work/scope.txt"
else
    echo_tool=/bin/echo
    expr_tool=/bin/expr
    ln_tool=/bin/ln
    openssl_tool=/usr/bin/openssl
    printf '%s\n' 'Default full-base tool paths.' > "$work/scope.txt"
fi
for tool in /bin/sh /bin/cat /usr/bin/awk "$echo_tool" "$expr_tool" "$ln_tool" /bin/ls \
    /bin/mkdir /bin/rm "$openssl_tool"; do
    [ -f "$tool" ] && [ -x "$tool" ]
    sha256 "$tool"
done > "$work/base-tools.sha256"
run_openssl() {
    if [ -n "$extra" ]; then
        env -i PATH=/bin:/usr/bin:/sbin:/usr/sbin LD_LIBRARY_PATH="$extra/lib" \
            "$openssl_tool" "$@"
    else
        env -i PATH=/bin:/usr/bin:/sbin:/usr/sbin "$openssl_tool" "$@"
    fi
}
run_openssl version -a > "$work/openssl.txt"
run_script() {
    # These documented environment overrides keep every write under NEW_WORK.
    # Start with an empty environment so host/query loader settings cannot leak.
    if [ -n "$extra" ]; then
        env -i PATH=/bin:/usr/bin:/sbin:/usr/sbin HOME="$work" \
            PREFIX="$prefix" DATADIR="$prefix/share/mozilla-rootcerts" \
            SSLDIR="$work/openssl" LD_LIBRARY_PATH="$extra/lib" \
            ECHO="$echo_tool" EXPR="$expr_tool" LN="$ln_tool" \
            OPENSSL="$openssl_tool" "$script" "$@"
    else
        env -i PATH=/bin:/usr/bin:/sbin:/usr/sbin HOME="$work" \
            PREFIX="$prefix" DATADIR="$prefix/share/mozilla-rootcerts" \
            SSLDIR="$work/openssl" "$script" "$@"
    fi
}
mkdir "$work/extract"
(cd "$work/extract" && run_script extract) > "$work/extract.log" 2>&1
(cd "$work/extract" && run_script rehash) > "$work/rehash.log" 2>&1
for pem in "$work/extract"/*.pem; do [ -f "$pem" ]; printf '%s\n' "$pem"; done \
    > "$work/extracted-pems.txt"
count=$(wc -l < "$work/extracted-pems.txt" | tr -d ' ')
[ "$count" -gt 100 ]
while IFS= read -r pem; do
    run_openssl x509 -in "$pem" -noout
    sha256 -q "$pem"
done < "$work/extracted-pems.txt" > "$work/extracted-unsorted.sha256"
sort "$work/extracted-unsorted.sha256" > "$work/extracted.sha256"
for link in "$work/extract"/*; do
    if [ -L "$link" ]; then printf '%s\n' "$link"; fi
done > "$work/extract-links.txt"
links=$(wc -l < "$work/extract-links.txt" | tr -d ' ')
[ "$links" -gt 100 ]
while IFS= read -r link; do [ -f "$link" ]; done < "$work/extract-links.txt"
run_script install > "$work/install.log" 2>&1
certs=$work/openssl/certs
[ -s "$certs/ca-certificates.crt" ]
for pem in "$certs"/*.pem; do [ -f "$pem" ]; printf '%s\n' "$pem"; done \
    > "$work/installed-pems.txt"
[ "$(wc -l < "$work/installed-pems.txt" | tr -d ' ')" = "$count" ]
while IFS= read -r pem; do sha256 -q "$pem"; done < "$work/installed-pems.txt" \
    > "$work/installed-unsorted.sha256"
sort "$work/installed-unsorted.sha256" > "$work/installed.sha256"
cmp "$work/extracted.sha256" "$work/installed.sha256"
[ "$(sha256 -q "$script")" = "$3" ]
[ "$(sha256 -q "$data")" = "$4" ]
printf 'PASS: %s certificates; %s verified rehash links; private-prefix install agrees\n' "$count" "$links"
