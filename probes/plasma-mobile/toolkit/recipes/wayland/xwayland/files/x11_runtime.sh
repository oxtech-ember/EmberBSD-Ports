#!@RCD_SCRIPTS_SHELL@
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Shared sockets for unprivileged Xwayland.

# PROVIDE: x11_runtime
# REQUIRE: mountall cleartmp
# BEFORE: DAEMON LOGIN

$_rc_subr_loaded . /etc/rc.subr

name="x11_runtime"
start_cmd="x11_runtime_start"
stop_cmd=":"

x11_runtime_check()
{
	if [ -L "$1" ] || [ ! -d "$1" ]; then
		warn "$1 must be a real directory."
		return 1
	fi
	mode=$(/usr/bin/stat -f '%u:%g:%p' "$1") || return 1
	if [ "$mode" != '0:0:41777' ]; then
		warn "$1 must have root:wheel ownership and mode 1777."
		return 1
	fi
}

x11_runtime_start()
{
	if [ "$(/usr/bin/id -u)" != 0 ]; then
		warn 'Run x11_runtime as root.'
		return 1
	fi
	# The root-owned sticky parent protects newly created root entries.
	# A per-user /tmp cannot provide these shared X11 socket paths.
	x11_runtime_check /tmp || return 1
	for directory in /tmp/.X11-unix /tmp/.ICE-unix; do
		if [ ! -e "$directory" ] && [ ! -L "$directory" ]; then
			/bin/mkdir -m 1777 "$directory" || return 1
			/sbin/chown -h root:wheel "$directory" || return 1
		fi
		# Do not follow links, take over another owner, or remove sockets.
		x11_runtime_check "$directory" || return 1
	done
}

load_rc_config $name
run_rc_command "$1"
