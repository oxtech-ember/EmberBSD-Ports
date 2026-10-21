#define _NETBSD_SOURCE 1

#include <stddef.h>
#include <sys/event.h>
#include <sys/statvfs.h>
#include <time.h>
#include <unistd.h>

_Static_assert(sizeof(struct kevent) == 72, "NetBSD kevent size");
_Static_assert(offsetof(struct kevent, ext) == 40, "NetBSD kevent extensions offset");
_Static_assert(sizeof(struct statvfs) == 3296, "NetBSD statvfs size");
_Static_assert(offsetof(struct statvfs, f_spare) == 160, "NetBSD statvfs spare offset");
_Static_assert(offsetof(struct statvfs, f_mntfromlabel) == 2272,
               "NetBSD statvfs label offset");

int
netbsd_abi_references(int kq, int fd, struct kevent *events, struct statvfs *stats)
{
	int duplicate;

	duplicate = dup3(fd, 1024, 0);
	if (duplicate >= 0 && close(duplicate) != 0)
		return -1;

	return kevent(kq, events, 0, events, 0, NULL) +
	    statvfs("/", stats) + fstatvfs(fd, stats);
}
