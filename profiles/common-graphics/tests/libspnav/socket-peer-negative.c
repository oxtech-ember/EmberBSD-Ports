/* SPDX-License-Identifier: BSD-2-Clause */
/* Origin: EmberBSD (AI-assisted); peer deadline controls, not a library mock. */
#define _POSIX_C_SOURCE 200809L
#define main socket_client_main
#include "socket-client.c"
#undef main
#include <signal.h>
#include <stdlib.h>

int
main(int argc, char **argv)
{
	const char *phase = getenv("SPNAV_NEGATIVE_PHASE");
	int result;

	if (phase == NULL || signal(SIGTERM, SIG_IGN) == SIG_ERR)
		return 2;
	if (strcmp(phase, "waitpid") == 0) {
		/* Complete the unchanged real client, then refuse to exit. */
		result = socket_client_main(argc, argv);
		if (result != 0)
			return result;
	} else if (strcmp(phase, "accept") != 0) {
		return 2;
	}
	for (;;)
		(void)pause();
}
