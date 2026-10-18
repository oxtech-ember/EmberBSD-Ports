#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Run at top level so every setup failure is fatal.
set -eu
PATH=/bin:/sbin:/usr/bin:/usr/sbin:/usr/pkg/bin
HOME=/root USER=root LOGNAME=root SHELL=/bin/sh
export PATH HOME USER LOGNAME SHELL
mount -u -w /
hostname ember-query
mount -t ptyfs ptyfs /dev/pts
ifconfig lo0 inet 127.0.0.1 up
ifconfig vioif0 inet 10.0.2.15 netmask 255.255.255.0 up
route add default 10.0.2.2
/usr/sbin/sshd -t
/usr/sbin/sshd
uname -a
df -ki /
printf '%s\n' EMBER_QUERY_SSH_READY
