/* SPDX-License-Identifier: BSD-2-Clause */
/* Origin: EmberBSD (AI-assisted), actual-source ownership contract. */

/* Include the real module to release its process-lifetime rules in this test. */
#include "fixup-libtool.c"

int
main(int argc, char **argv)
{
	struct arglist args;
	struct argument *arg;
	struct unwrap_rule *rule;

	if (argc != 3)
		errx(1, "usage: cwrappers-unwrap source:destination archive.la");
	register_unwrap(argv[1]);
	TAILQ_INIT(&args);
	arg = argument_copy("-o");
	TAILQ_INSERT_TAIL(&args, arg, link);
	arg = argument_copy(argv[2]);
	TAILQ_INSERT_TAIL(&args, arg, link);
	fixup_libtool(&args);
	while ((arg = TAILQ_FIRST(&args)) != NULL)
		argument_unlink(&args, &arg);
	while ((rule = TAILQ_FIRST(&unwrap_rules)) != NULL) {
		TAILQ_REMOVE(&unwrap_rules, rule, link);
		free(rule->src);
		free(rule->dst);
		free(rule);
	}
	return 0;
}
