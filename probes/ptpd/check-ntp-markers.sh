#!/bin/sh
# Run ptpd2 in the foreground and fail when it changes the kernel NTP state,
# judged by markers. This is the check for a static ptpd2, which the
# ntptrace.so shim cannot enter. Run it as root on a target where no other
# process writes the NTP state (no chronyd or ntpd), with peers that drive
# ptpd2 into the state under test.
#
#	check-ntp-markers.sh CONFIG SECONDS WORKDIR STATE [PTPD2]
#
# Before the run the script sets the TAI offset to 11 s, esterror to
# 4242 us and maxerror to 100000 us. Without writes the kernel keeps the
# status word, the TAI offset and esterror, and only grows maxerror; a
# ptpd2 write changes one of the first three or lowers maxerror. STATE is
# the port state the run must reach, as in check-ntp-owner.sh. WORKDIR
# receives ptpd2.out (console log), states, and state.before and
# state.after (ntpstate output). Exit status: 0 when ptpd2 reached STATE
# and kept the markers; 1 when a marker changed; 2 on a usage or run error.
#
# SPDX-License-Identifier: BSD-2-Clause
# AI-assisted (Claude Code, Claude Opus 5.5).

set -u
[ "$#" -ge 4 ] || { echo "usage: $0 CONFIG SECONDS WORKDIR STATE [PTPD2]" >&2; exit 2; }
config=$1 seconds=$2 work=$3 expect=$4 ptpd2=${5:-/usr/pkg/sbin/ptpd2}
here=$(dirname "$0")
ntpstate=${NTPSTATE:-$here/ntpstate}
[ -r "$config" ] && [ -x "$ptpd2" ] && [ -x "$ntpstate" ] || {
	echo "$0: missing configuration, ptpd2 or ntpstate" >&2; exit 2; }
for owner in chronyd ntpd; do
	! pgrep -x "$owner" > /dev/null || {
		echo "$0: $owner runs and rewrites the markers; use check-ntp-owner.sh" >&2; exit 2; }
done
mkdir -p "$work" || exit 2

# ptpd2 reports its states in global:log_file when one is configured.
log=$(sed -n 's/^[[:space:]]*global:log_file[[:space:]]*=[[:space:]]*//p' "$config" | tail -1)
logsize=0
[ -n "$log" ] && [ -f "$log" ] && logsize=$(wc -c < "$log")

"$ntpstate" set tai=11 esterror=4242 maxerror=100000 > /dev/null || exit 2
"$ntpstate" > "$work/state.before" || exit 2
"$ptpd2" -C -c "$config" > "$work/ptpd2.out" 2>&1 &
pid=$!
sleep "$seconds"
kill -TERM "$pid" 2>/dev/null || { echo "$0: ptpd2 exited early" >&2; cat "$work/ptpd2.out" >&2; exit 2; }
wait "$pid" || { echo "$0: ptpd2 failed on SIGTERM" >&2; exit 2; }
"$ntpstate" > "$work/state.after" || exit 2

{ cat "$work/ptpd2.out"; [ -n "$log" ] && tail -c +$((logsize + 1)) "$log"; } |
    grep -o 'Now in state: PTP_[A-Z]*' > "$work/states"
states=$(sed 's/.* //' "$work/states" | uniq | tr '\n' ' ')
field() { tr ' ' '\n' < "$2" | sed -n "s/^$1=//p"; }
changed=
for f in status tai esterror; do
	[ "$(field $f "$work/state.before")" = "$(field $f "$work/state.after")" ] || changed="$changed $f"
done
[ "$(field maxerror "$work/state.after")" -ge "$(field maxerror "$work/state.before")" ] ||
    changed="$changed maxerror"
echo "states: $states"
echo "before: $(cat "$work/state.before")"
echo "after:  $(cat "$work/state.after")"
grep -qx "Now in state: $expect" "$work/states" || {
	echo "$0: ptpd2 did not reach $expect" >&2; exit 2; }
[ -z "$changed" ] || { echo "changed:$changed"; exit 1; }
exit 0
