#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). One executable for pkgsrc TOOLS_SORT users.
LC_ALL=C
export LC_ALL
exec /usr/bin/sort "$@"
