#!@RCD_SCRIPTS_SHELL@
#
# $NetBSD$
#
# PROVIDE: ptpd2
# REQUIRE: NETWORKING ntpd chronyd
# KEYWORD: shutdown
#
# A master serves the system clock, so it starts after the daemon that
# disciplines that clock; that daemon may still be synchronising. Without
# chrony, rcorder(8) warns that chronyd has no provider and exits 1, and
# keeps the order of the other scripts.
#
# In /etc/rc.conf:
#	ptpd2=YES
#	ptpd2_config=@PKG_SYSCONFDIR@/ptpd2.conf	(default)
#
# The configuration keeps the default lock file /var/run/ptpd2.lock:
# ptpd2 writes its PID there after it detaches.

. /etc/rc.subr

name="ptpd2"
rcvar=$name
command="@PREFIX@/sbin/${name}"
pidfile="/var/run/${name}.lock"

load_rc_config $name
: ${ptpd2_config:="@PKG_SYSCONFDIR@/${name}.conf"}
required_files="$ptpd2_config"
command_args="-c $ptpd2_config"
run_rc_command "$1"
