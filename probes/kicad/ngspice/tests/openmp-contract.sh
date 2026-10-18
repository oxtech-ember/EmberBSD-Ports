#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted); real BSIM4 workload and kernel thread traces.
set -eu
[ "$#" = 2 ] || { echo 'Usage: openmp-contract.sh ABS_NGSPICE ABS_NEW_OUTPUT' >&2; exit 2; }
ngspice=$1
output=$2
case "$ngspice:$output" in /*:/*) ;; *) exit 2;; esac
case "$ngspice$output" in *[!A-Za-z0-9_./-]*) exit 2;; esac
[ ! -e "$output" ] && [ ! -L "$output" ] || exit 2
here=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
source=$here/bsim4-upstream.sp
[ "$(sha256 -q "$source")" = 817b8ed1a1879fce346a1750268fbca0005e759a68fa1d41204fcbf3c3f38ecb ]
command -v ktrace >/dev/null
command -v kdump >/dev/null
mkdir "$output"
LC_ALL=C
OMP_DYNAMIC=FALSE
OMP_THREAD_LIMIT=2
export LC_ALL OMP_DYNAMIC OMP_THREAD_LIMIT
for threads in 1 2; do
    deck=$output/input-$threads.cir
    # Retain every upstream device/model line. Replace only interactive control.
    awk '/^\.control$/ {found=1; exit} {print} END {if (!found) exit 1}' "$source" > "$deck"
    cat >> "$deck" <<EOF
.control
set num_threads=$threads
dc vgsn 0 1.5 0.05
wrdata dc-$threads.dat v(1) vssn#branch
quit
.endc
.end
EOF
    (
        cd "$output"
        ktrace -t c -f "$output/threads-$threads.ktrace" \
            "$ngspice" --no-spiceinit -b "$deck" > "$output/run-$threads.log" 2>&1
    )
    kdump -f "$output/threads-$threads.ktrace" > "$output/threads-$threads.log"
    awk '
    /RET[[:space:]]+_lwp_create[[:space:]]+0([[:space:]]|$)/ {count++}
    END {print count+0}
    ' "$output/threads-$threads.log" > "$output/workers-$threads.txt"
    awk '
    function abs(x) {return x < 0 ? -x : x}
    NF != 4 || tolower($0) ~ /nan|inf/ {bad=1; exit 1}
    {
        for (i=1; i<=4; i++) {
            if ($i !~ /^[+-]?([0-9]+([.][0-9]*)?|[.][0-9]+)([eE][+-]?[0-9]+)?$/ ||
                tolower(sprintf("%.17g", $i+0)) ~ /nan|inf/) {bad=1; exit 1}
            # Some AWK implementations return zero for an out-of-range token.
            mantissa=$i; sub(/[eE].*$/, "", mantissa)
            if (($i+0)==0 && mantissa ~ /[1-9]/) {bad=1; exit 1}
        }
        expected=(NR-1)*.05
        for (i=1; i<=3; i++) if (abs($i-expected)>1e-10) {bad=1; exit 1}
        if (abs($4)>1e-18) nonzero=1
    }
    END {if (bad || NR!=31 || !nonzero) exit 1}
    ' "$output/dc-$threads.dat"
done
awk '
function abs(x) {return x < 0 ? -x : x}
NR==FNR {for (i=1;i<=NF;i++) saved[FNR,i]=$i; rows=FNR; next}
{
    for (i=1;i<=NF;i++) {
        a=saved[FNR,i]; b=$i; scale=abs(a)>abs(b) ? abs(a) : abs(b)
        if (abs(a-b)>1e-12+1e-8*scale) {bad=1; exit 1}
    }
}
END {if (bad || FNR!=rows) exit 1}
' "$output/dc-1.dat" "$output/dc-2.dat"
serial=$(cat "$output/workers-1.txt")
parallel=$(cat "$output/workers-2.txt")
[ "$parallel" -gt "$serial" ]
printf 'PASS: BSIM4 one/two-thread DC results agree; successful LWP creations %s -> %s\n' "$serial" "$parallel"
