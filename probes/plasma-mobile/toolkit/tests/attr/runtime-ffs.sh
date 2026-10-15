#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Use an isolated FFS2ea runtime fixture.
# The format follows EmberBSD tests/fs/ffs/t_extattr.c and
# tests/sbin/fsck_ffs/t_extattr.sh. It never converts an existing filesystem.
set -eu
PATH=/bin:/usr/bin:/sbin:/usr/sbin
export PATH
LC_ALL=C
export LC_ALL
umask 077
[ "$#" -eq 5 ] || { echo "Usage: $0 PREFIX NEW_OUTPUT CONSUMER UNUSED_VND USER" >&2; exit 2; }
prefix=$1 output=$2 consumer=$3 vnd=$4 account=$5
case "$prefix:$output:$consumer" in /*:/*:/*) ;; *) echo 'Use absolute paths' >&2; exit 2 ;; esac
case "$prefix$output$consumer$account" in *[!A-Za-z0-9_./-]*) echo 'Use paths and account names without shell metacharacters or spaces' >&2; exit 2 ;; esac
case "$vnd" in vnd*) unit=${vnd#vnd} ;; *) exit 2 ;; esac
case "$unit" in ''|*[!0-9]*) exit 2 ;; esac
[ "$(id -u)" -eq 0 ] || { echo 'Run the filesystem fixture as root' >&2; exit 2; }
account_id=$(id -u "$account")
[ "$account_id" -ne 0 ] || { echo 'Select an unprivileged runtime account' >&2; exit 2; }
[ -x "$consumer" ]
runner=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)/runtime.sh
[ -f "$runner" ]
for tool in vnconfig newfs mount umount su sysctl; do command -v "$tool" >/dev/null; done
raw_partition=$(sysctl -n kern.rawpartition)
case "$raw_partition" in 0|1|2|3|4|5|6|7|8|9|10|11|12|13|14|15) ;; *) echo 'Unknown raw partition' >&2; exit 2 ;; esac
set -- a b c d e f g h i j k l m n o p
shift "$raw_partition"
block_device=/dev/${vnd}$1
[ -b "$block_device" ] || { echo "Not a block device: $block_device" >&2; exit 2; }
mkdir "$output"
chmod 0711 "$output"
image=$output/fixture.ffs
point=$output/mnt
attached=no
mounted=no
keep_image=no
cleanup() {
    fixture_result=$?
    if [ "$fixture_result" -ne 0 ]; then keep_image=yes; fi
    trap - 0 HUP INT TERM
    if [ "$mounted" = yes ]; then
        if [ -d "$point/run" ]; then
            cp -Rp "$point/run" "$output/runtime" || { keep_image=yes; fixture_result=1; }
        fi
        if umount "$point" >> "$output/cleanup.log" 2>&1; then
            mounted=no
        else
            echo "Unmount failed; preserve $image and $vnd" >&2
            exit 1
        fi
    fi
    if [ "$attached" = yes ]; then
        if vnconfig -u "$vnd" >> "$output/cleanup.log" 2>&1; then
            attached=no
        else
            echo "Detach failed; preserve $image and $vnd" >&2
            exit 1
        fi
    fi
    if [ "$keep_image" = no ]; then rm -f "$image"; fi
    df -k "$output" > "$output/space-after.txt"
    exit "$fixture_result"
}
trap cleanup 0
trap 'exit 129' HUP
trap 'exit 130' INT
trap 'exit 143' TERM
# An unknown or busy device must not be detached or reused.
vnconfig -l -m 1 "$vnd" > "$output/vnd-before.txt"
[ "$(cat "$output/vnd-before.txt")" = "$vnd: not in use" ] || { echo "$vnd is not free" >&2; exit 1; }
df -k "$output" > "$output/space-before.txt"
printf '%s\n' "$block_device" > "$output/block-device.txt"
newfs -O2ea -b 8k -f 1k -s 4m -F "$image" > "$output/newfs.log" 2>&1
vnconfig "$vnd" "$image" > "$output/attach.log" 2>&1
attached=yes
mkdir "$point"
mount -t ffs "$block_device" "$point" > "$output/mount.log" 2>&1
mounted=yes
chown "$account_id" "$point"
chmod 0700 "$point"
mkdir "$output/programs"
chmod 0755 "$output/programs"
cp "$consumer" "$output/programs/consumer"
cp "$runner" "$output/programs/runtime.sh"
chmod 0555 "$output/programs/consumer" "$output/programs/runtime.sh"
# Arguments were restricted above. The account runs only this new test data.
su -m "$account" -c "/bin/sh '$output/programs/runtime.sh' '$prefix' '$point/run' '$output/programs/consumer'" > "$output/runtime.log" 2>&1
