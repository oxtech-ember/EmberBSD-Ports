#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted).
set -eu
[ "$#" = 2 ] || { echo 'Usage: cli-contract.sh ABS_NGSPICE ABS_NEW_OUTPUT' >&2; exit 2; }
ngspice=$1
output=$2
case "$ngspice:$output" in /*:/*) ;; *) exit 2 ;; esac
[ ! -e "$output" ] && [ ! -L "$output" ] || exit 2
here=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
mkdir "$output"
"$ngspice" --version > "$output/version.log"
grep 'ngspice-47' "$output/version.log" >/dev/null
set --
i=0
while [ "$i" -lt 96 ]; do
    set -- "$@" -c "$here/divider.cir"
    i=$((i + 1))
done
(
    ulimit -n 32
    "$ngspice" --no-spiceinit -b "$@" "$here/divider.cir" > "$output/repeated-c.log" 2>&1
)
awk '
/v\(vin\) =/ {if (($3 + 0) != 10) exit 1; vin=1}
/v\(vout\) =/ {if (($3 + 0) != 4) exit 1; vout=1}
/i\(v1\) =/ {d=($3 + 0) + .002; if (d < -1e-12 || d > 1e-12) exit 1; current=1}
END {if (!(vin && vout && current)) exit 1}
' "$output/repeated-c.log"
cat > "$output/malformed.cir" <<'CIR'
Malformed vector expression
V1 in 0 DC 1
R1 in 0 1k
.dc V1 0 1 1
.print dc v(in,out
.end
CIR
status=0
"$ngspice" --no-spiceinit -b "$output/malformed.cir" > "$output/malformed.log" 2>&1 || status=$?
[ "$status" = 1 ]
grep "missing ')'" "$output/malformed.log" >/dev/null
printf '%s\n' 'PASS: installed CLI version, repeated -c, analytic divider and malformed vector'
