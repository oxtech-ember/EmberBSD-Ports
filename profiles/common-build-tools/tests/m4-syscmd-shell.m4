dnl SPDX-License-Identifier: BSD-2-Clause
dnl Copyright (c) 2026 EmberBSD contributors.
dnl Requires the explicitly selected mksh. It does not run an external command.
changequote([,])dnl
syscmd([print -r -- m4-syscmd])dnl
sysval
esyscmd([print -r -- m4-esyscmd])dnl
syscmd([exit 7])dnl
sysval
esyscmd([exit 9])dnl
sysval
