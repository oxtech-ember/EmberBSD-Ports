/*
 * Link this wrapper with the real mksh objects and --wrap=evaluate.
 * Use the compiler flags from Build.sh and the Valgrind include directory.
 * The normal shell must process the invalid and valid arithmetic inputs.
 * Origin: EmberBSD, AI-assisted. SPDX-License-Identifier: ISC
 */

#include "sh.h"

#include <memcheck.h>

int __real_evaluate(const char *, mksh_ari_t *, int, bool);
int __wrap_evaluate(const char *, mksh_ari_t *, int, bool);

int
__wrap_evaluate(const char *expr, mksh_ari_t *rval, int error_ok, bool arith)
{
	const mksh_ari_t sentinel = 0x5A5A;
	int ret;

	*rval = sentinel;
	ret = __real_evaluate(expr, rval, error_ok, arith);
	if (!ret) {
		if (VALGRIND_CHECK_MEM_IS_DEFINED(rval, sizeof(*rval)) != 0 ||
		    *rval != sentinel) {
			fputs("FAIL evaluate changed the result after an error\n",
			    stderr);
			exit(98);
		}
		fputs("PASS evaluate preserved the result after an error\n",
		    stderr);
	}
	return (ret);
}
