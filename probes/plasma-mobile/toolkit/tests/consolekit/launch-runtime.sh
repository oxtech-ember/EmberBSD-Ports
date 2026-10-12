#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), real ConsoleKit launcher regression.
set -eu
[ "$#" = 1 ] || { echo 'Usage: launch-runtime.sh NEW_OUTPUT' >&2; exit 2; }
PATH=/usr/pkg/bin:/usr/pkg/sbin:/usr/bin:/usr/sbin:/bin:/sbin; export PATH
[ "$(id -u)" = 0 ] || { echo 'The test daemon requires root.' >&2; exit 2; }
# ConsoleKit uses global runtime state even with a private D-Bus address.
# Do not run beside a real login service or replace an existing PID file.
[ ! -e /var/run/ConsoleKit/pid ] || { echo 'Existing ConsoleKit PID file' >&2; exit 2; }
if ps -axww -o comm | grep -q 'console-kit-daemon'; then
    echo 'Existing ConsoleKit daemon' >&2; exit 2
fi
umask 077
mkdir "$1"
work=$(CDPATH= cd -- "$1" && pwd)
cd "$work"
ulimit -c 0
sysctl kern.boottime > boot.before
pkg_info -e consolekit > packages.txt
pkg_info -e polkit >> packages.txt
cat > child.sh <<'EOF'
#!/bin/sh
set -eu
[ -n "${XDG_SESSION_COOKIE:-}" ] || exit 91
gdbus call --system --dest org.freedesktop.ConsoleKit \
    --object-path /org/freedesktop/ConsoleKit/Manager \
    --method org.freedesktop.ConsoleKit.Manager.GetSessionForCookie \
    "$XDG_SESSION_COOKIE" | grep -q /org/freedesktop/ConsoleKit/Session
case "${1:-default}" in
    success) ck-list-sessions; exit 0 ;;
    signal) kill -TERM "$$" ;;
    missing) exit 92 ;;
    *) exit 42 ;;
esac
EOF
chmod 700 child.sh
cat > checks.sh <<'EOF'
#!/bin/sh
set -eu
DBUS_SYSTEM_BUS_ADDRESS=$DBUS_SESSION_BUS_ADDRESS; export DBUS_SYSTEM_BUS_ADDRESS
console-kit-daemon --no-daemon --debug > daemon.log 2>&1 &
ckpid=$!
cleanup()
{
    kill "$ckpid" 2>/dev/null || :
    count=0
    while kill -0 "$ckpid" 2>/dev/null && [ "$count" -lt 5 ]; do
        sleep 1; count=$((count + 1))
    done
    if kill -0 "$ckpid" 2>/dev/null; then kill -KILL "$ckpid"; fi
    wait "$ckpid" 2>/dev/null || :
    # Upstream uses a default SIGTERM disposition; atexit does not remove its PID.
    # Remove only our exact, now-dead daemon's file.
    if [ -f /var/run/ConsoleKit/pid ] &&
        [ "$(cat /var/run/ConsoleKit/pid)" = "$ckpid" ] &&
        ! kill -0 "$ckpid" 2>/dev/null; then
        rm /var/run/ConsoleKit/pid
    fi
}
trap cleanup EXIT
trap 'exit 1' HUP INT TERM
gdbus wait --system --timeout 10 org.freedesktop.ConsoleKit
kill -0 "$ckpid"
expect()
{
    label=$1 expected=$2; shift 2
    actual=0
    "$@" > "$label.log" 2>&1 || actual=$?
    printf '%s\n' "$actual" > "$label.status"
    if [ "$actual" != "$expected" ]; then
        echo "FAIL: $label expected=$expected actual=$actual" >&2
        cat "$label.log" >&2
        exit 1
    fi
    echo "PASS: $label status=$actual"
}
expect success 0 ck-launch-session -- "$PWD/child.sh" success
grep -q 'Session' success.log
expect exit42 42 ck-launch-session -- "$PWD/child.sh" failure
expect signal 143 ck-launch-session -- "$PWD/child.sh" signal
expect default-shell 42 env SHELL="$PWD/child.sh" ck-launch-session
expect service 42 ck-launch-session --service ember-acceptance -- "$PWD/child.sh" failure
expect missing-command 1 ck-launch-session -- "$PWD/nonexistent-command"
expect unknown-option 1 ck-launch-session --ember-unknown-option
# Sessions close asynchronously when their owner disconnects.
count=0
while :; do
    if ! gdbus call --system --dest org.freedesktop.ConsoleKit \
        --object-path /org/freedesktop/ConsoleKit/Manager \
        --method org.freedesktop.ConsoleKit.Manager.GetSessions > sessions.after 2>&1; then
        grep -q Error.NoSessions sessions.after
        break
    fi
    count=$((count + 1)); [ "$count" -lt 10 ] || exit 1
    sleep 1
done
echo 'PASS: no sessions remain after child exit'
EOF
chmod 700 checks.sh
result=0
timeout -k 5 90 dbus-run-session -- ./checks.sh > checks.log 2>&1 || result=$?
printf '%s\n' "$result" > status
cat checks.log
sysctl kern.boottime > boot.after
cmp boot.before boot.after
[ ! -e /var/run/ConsoleKit/pid ]
[ "$result" = 0 ] || exit "$result"
echo 'PASS: real private-bus session creation, launcher status and cleanup; no authentication, VT or power-management acceptance'
