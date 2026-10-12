#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), installed KWallet and upstream crypto tests.
set -eu
[ "$#" = 2 ] || { echo 'Usage: kwallet-runtime.sh UPSTREAM_BINARIES NEW_OUTPUT' >&2; exit 2; }
binaries=$(CDPATH= cd -- "$1" && pwd)
for program in fdo_secrets_test blowfishtest; do
    [ -x "$binaries/$program" ]
done
umask 077
mkdir "$2"
work=$(CDPATH= cd -- "$2" && pwd)
PATH=/usr/pkg/bin:/usr/pkg/sbin:/usr/bin:/usr/sbin:/bin:/sbin; export PATH
ulimit -c 0
mkdir "$work/home" "$work/runtime"
sysctl kern.boottime > "$work/boot.before"
pkg_info -e kf6-kwallet > "$work/package.txt"
for program in fdo_secrets_test blowfishtest; do
    ldd "$binaries/$program" > "$work/$program.ldd"
    ! grep -q 'not found' "$work/$program.ldd"
    sha256 "$binaries/$program" >> "$work/inputs.sha256"
    result=0
    # The upstream FDO suite mocks storage but uses the real QCA/OpenSSL code.
    timeout -k 5 180 env -i PATH="$PATH" HOME="$work/home" LC_ALL=C.UTF-8 \
        XDG_RUNTIME_DIR="$work/runtime" QT_QPA_PLATFORM=minimal \
        dbus-run-session -- "$binaries/$program" > "$work/$program.log" 2>&1 || result=$?
    printf '%s\n' "$result" > "$work/$program.status"
    cat "$work/$program.log"
    [ "$result" = 0 ] || exit "$result"
done
# Exercise the installed daemon and both upstream activation aliases on a fresh
# private bus. No user's bus, wallet, credentials or persistent settings are used.
cat > "$work/activate.sh" <<'ACTIVATE'
#!/bin/sh
set -eu
cleanup()
{
    # ksecretd may survive the bus disconnect; stop only owners on this test bus.
    for service in "org.kde.kwalletd$1" org.kde.secretservicecompat; do
        pid=$(dbus-send --session --print-reply --reply-timeout=3000 \
            --dest=org.freedesktop.DBus /org/freedesktop/DBus \
            org.freedesktop.DBus.GetConnectionUnixProcessID string:"$service" \
            2>/dev/null | awk '/uint32/ {print $2}')
        case "$pid" in ''|*[!0-9]*) continue ;; esac
        kill "$pid" 2>/dev/null || :
    done
}
trap 'cleanup "$1"' EXIT HUP INT TERM
dbus-send --session --print-reply --reply-timeout=15000 \
    --dest="org.kde.kwalletd$1" "/modules/kwalletd$1" \
    org.kde.KWallet.isEnabled > "alias-$1.log"
grep -q 'boolean true' "alias-$1.log"
ACTIVATE
(
    cd "$work"
    timeout -k 5 60 env -i PATH="$PATH" HOME="$work/home" LC_ALL=C.UTF-8 \
        XDG_RUNTIME_DIR="$work/runtime" QT_QPA_PLATFORM=minimal \
            dbus-run-session -- sh ./activate.sh 5
timeout -k 5 60 env -i PATH="$PATH" HOME="$work/home" LC_ALL=C.UTF-8 \
    XDG_RUNTIME_DIR="$work/runtime" QT_QPA_PLATFORM=minimal \
    dbus-run-session -- sh ./activate.sh 6
) > "$work/activation.log" 2>&1
cat "$work/activation.log"
sysctl kern.boottime > "$work/boot.after"
cmp "$work/boot.before" "$work/boot.after"
echo 'PASS: upstream crypto/storage-mock tests and installed KWallet D-Bus aliases; interactive storage is not tested'
