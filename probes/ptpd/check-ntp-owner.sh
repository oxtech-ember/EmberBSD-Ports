#!/bin/sh
# Run ptpd2 in the foreground with the ntptrace.so shim and fail when it
# changes the system clock or the kernel NTP state. Run it as root on the
# target, next to the clock owner (for example chronyd), with peers that
# drive ptpd2 into the state under test.
#
#	check-ntp-owner.sh SHIM CONFIG SECONDS WORKDIR STATE [PTPD2]
#
# STATE is the port state the run must reach, for example PTP_PASSIVE: a
# master that never leaves PTP_MASTER has nothing to write, so such a run
# proves nothing. WORKDIR receives ptpd2.out (console log), trace.log (shim
# log), states, and state.before and state.after (ntpstate output). Exit
# status: 0 when ptpd2 reached STATE, read the NTP state through the shim
# and made no such call; 1 when it made one; 2 on a usage or run error.
#
# SPDX-License-Identifier: BSD-2-Clause
# AI-assisted (Claude Code, Claude Opus 5.5).

set -u
[ "$#" -ge 5 ] || { echo "usage: $0 SHIM CONFIG SECONDS WORKDIR STATE [PTPD2]" >&2; exit 2; }
shim=$1 config=$2 seconds=$3 work=$4 expect=$5 ptpd2=${6:-/usr/pkg/sbin/ptpd2}
here=$(dirname "$0")
ntpstate=${NTPSTATE:-$here/ntpstate}
[ -r "$shim" ] && [ -r "$config" ] && [ -x "$ptpd2" ] && [ -x "$ntpstate" ] || {
	echo "$0: missing shim, configuration, ptpd2 or ntpstate" >&2; exit 2; }
mkdir -p "$work" || exit 2
rm -f "$work/trace.log"

# ptpd2 reports its states in global:log_file when one is configured.
log=$(sed -n 's/^[[:space:]]*global:log_file[[:space:]]*=[[:space:]]*//p' "$config" | tail -1)
logsize=0
[ -n "$log" ] && [ -f "$log" ] && logsize=$(wc -c < "$log")

"$ntpstate" > "$work/state.before" || exit 2
env LD_PRELOAD="$shim" NTPTRACE_LOG="$work/trace.log" \
    "$ptpd2" -C -c "$config" > "$work/ptpd2.out" 2>&1 &
pid=$!
sleep "$seconds"
kill -TERM "$pid" 2>/dev/null || { echo "$0: ptpd2 exited early" >&2; cat "$work/ptpd2.out" >&2; exit 2; }
wait "$pid" || { echo "$0: ptpd2 failed on SIGTERM" >&2; exit 2; }
"$ntpstate" > "$work/state.after" || exit 2

grep -q ' exit ntp_adjtime_reads=' "$work/trace.log" 2>/dev/null || {
	echo "$0: the shim did not run in ptpd2" >&2; exit 2; }
{ cat "$work/ptpd2.out"; [ -n "$log" ] && tail -c +$((logsize + 1)) "$log"; } |
    grep -o 'Now in state: PTP_[A-Z]*' > "$work/states"
states=$(sed 's/.* //' "$work/states" | uniq | tr '\n' ' ')
writes=$(grep -vc ' exit ntp_adjtime_reads=' "$work/trace.log")
reads=$(sed -n 's/.* exit ntp_adjtime_reads=//p' "$work/trace.log")
echo "states: $states"
echo "clock or NTP state writes: $writes (ntp_adjtime_reads=$reads)"
echo "before: $(cat "$work/state.before")"
echo "after:  $(cat "$work/state.after")"
grep -qx "Now in state: $expect" "$work/states" || {
	echo "$0: ptpd2 did not reach $expect" >&2; exit 2; }
[ "$reads" -gt 0 ] || { echo "$0: ptpd2 read no NTP state through the shim" >&2; exit 2; }
[ "$writes" -eq 0 ] || { grep -v ' exit ntp_adjtime_reads=' "$work/trace.log"; exit 1; }
exit 0
