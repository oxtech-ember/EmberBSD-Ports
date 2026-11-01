/* Origin: EmberBSD; AI-assisted PowerVR Services ABI experiment. */
/* SPDX-License-Identifier: BSD-2-Clause */

#include <errno.h>

#include "errno_abi.h"

static _Thread_local int foreign_error;

static int
translate(int native_error)
{
	switch (native_error) {
	case 0:
		return 0;
	case EPERM:
		return 1;
	case ENOENT:
		return 2;
	case ESRCH:
		return 3;
	case EINTR:
		return 4;
	case EIO:
		return 5;
	case ENXIO:
		return 6;
	case E2BIG:
		return 7;
	case ENOEXEC:
		return 8;
	case EBADF:
		return 9;
	case ECHILD:
		return 10;
	case EDEADLK:
		return 35;
	case ENOMEM:
		return 12;
	case EACCES:
		return 13;
	case EFAULT:
		return 14;
	case ENOTBLK:
		return 15;
	case EBUSY:
		return 16;
	case EEXIST:
		return 17;
	case EXDEV:
		return 18;
	case ENODEV:
		return 19;
	case ENOTDIR:
		return 20;
	case EISDIR:
		return 21;
	case EINVAL:
		return 22;
	case ENFILE:
		return 23;
	case EMFILE:
		return 24;
	case ENOTTY:
		return 25;
	case ETXTBSY:
		return 26;
	case EFBIG:
		return 27;
	case ENOSPC:
		return 28;
	case ESPIPE:
		return 29;
	case EROFS:
		return 30;
	case EMLINK:
		return 31;
	case EPIPE:
		return 32;
	case EDOM:
		return 33;
	case ERANGE:
		return 34;
	case EAGAIN:
		return 11;
	case EINPROGRESS:
		return 115;
	case EALREADY:
		return 114;
	case ENOTSOCK:
		return 88;
	case EDESTADDRREQ:
		return 89;
	case EMSGSIZE:
		return 90;
	case EPROTOTYPE:
		return 91;
	case ENOPROTOOPT:
		return 92;
	case EPROTONOSUPPORT:
		return 93;
	case ESOCKTNOSUPPORT:
		return 94;
	case EOPNOTSUPP:
		return 95;
	case EPFNOSUPPORT:
		return 96;
	case EAFNOSUPPORT:
		return 97;
	case EADDRINUSE:
		return 98;
	case EADDRNOTAVAIL:
		return 99;
	case ENETDOWN:
		return 100;
	case ENETUNREACH:
		return 101;
	case ENETRESET:
		return 102;
	case ECONNABORTED:
		return 103;
	case ECONNRESET:
		return 104;
	case ENOBUFS:
		return 105;
	case EISCONN:
		return 106;
	case ENOTCONN:
		return 107;
	case ESHUTDOWN:
		return 108;
	case ETOOMANYREFS:
		return 109;
	case ETIMEDOUT:
		return 110;
	case ECONNREFUSED:
		return 111;
	case ELOOP:
		return 40;
	case ENAMETOOLONG:
		return 36;
	case EHOSTDOWN:
		return 112;
	case EHOSTUNREACH:
		return 113;
	case ENOTEMPTY:
		return 39;
	case EUSERS:
		return 87;
	case EDQUOT:
		return 122;
	case ESTALE:
		return 116;
	case EREMOTE:
		return 66;
	case ENOLCK:
		return 37;
	case ENOSYS:
		return 38;
	case EIDRM:
		return 43;
	case ENOMSG:
		return 42;
	case EOVERFLOW:
		return 75;
	case EILSEQ:
		return 84;
	case ECANCELED:
		return 125;
	case EBADMSG:
		return 74;
	case ENODATA:
		return 61;
	case ENOSR:
		return 63;
	case ENOSTR:
		return 60;
	case ETIME:
		return 62;
	case EMULTIHOP:
		return 72;
	case ENOLINK:
		return 67;
	case EPROTO:
		return 71;
	case EOWNERDEAD:
		return 130;
	case ENOTRECOVERABLE:
		return 131;
#if ENOTSUP != EOPNOTSUPP
	case ENOTSUP:
		return 95;
#endif
	default:
		return -1;
	}
}

int *
pvr_abi_errno_location(void)
{
	return &foreign_error;
}

int
pvr_abi_errno_from_native(int native_error)
{
	return translate(native_error);
}

int
pvr_abi_errno_set_native(int native_error)
{
	int translated = translate(native_error);

	if (translated < 0)
		return -1;
	foreign_error = translated;
	return 0;
}
