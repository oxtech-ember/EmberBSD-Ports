/*
 * Print or set the kernel NTP state for a PTPd check.
 *
 *	ntpstate			print one line
 *	ntpstate set NAME=VALUE...	set maxerror, esterror (us),
 *					status (number) or tai (s)
 *
 * SPDX-License-Identifier: BSD-2-Clause
 * AI-assisted (Claude Code, Claude Opus 5.5).
 */

#include <sys/time.h>
#include <sys/timex.h>

#include <err.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static long
number(const char *s)
{
	char *end;
	long v;

	v = strtol(s, &end, 0);
	if (*s == '\0' || *end != '\0')
		errx(2, "not a number: %s", s);
	return v;
}

int
main(int argc, char **argv)
{
	struct ntptimeval ntv;
	struct timex tx;
	int i, state;

	memset(&tx, 0, sizeof(tx));
	if (argc > 1) {
		if (strcmp(argv[1], "set") != 0 || argc < 3)
			errx(2, "usage: ntpstate [set NAME=VALUE...]");
		for (i = 2; i < argc; i++) {
			if (strncmp(argv[i], "maxerror=", 9) == 0) {
				tx.modes |= MOD_MAXERROR;
				tx.maxerror = number(argv[i] + 9);
			} else if (strncmp(argv[i], "esterror=", 9) == 0) {
				tx.modes |= MOD_ESTERROR;
				tx.esterror = number(argv[i] + 9);
			} else if (strncmp(argv[i], "status=", 7) == 0) {
				tx.modes |= MOD_STATUS;
				tx.status = (int)number(argv[i] + 7);
			} else if (strncmp(argv[i], "tai=", 4) == 0) {
				tx.modes |= MOD_TAI;
				tx.constant = number(argv[i] + 4);
			} else
				errx(2, "unknown field: %s", argv[i]);
		}
	}
	if ((state = ntp_adjtime(&tx)) == -1)
		err(1, "ntp_adjtime");
	if (argc > 1) {
		memset(&tx, 0, sizeof(tx));
		if ((state = ntp_adjtime(&tx)) == -1)
			err(1, "ntp_adjtime");
	}
	if (ntp_gettime(&ntv) == -1)
		err(1, "ntp_gettime");
	printf("state=%d status=0x%04x maxerror=%ld esterror=%ld tai=%ld "
	    "freq=%ld offset=%ld\n", state, tx.status, tx.maxerror,
	    tx.esterror, (long)ntv.tai, tx.freq, tx.offset);
	return 0;
}
