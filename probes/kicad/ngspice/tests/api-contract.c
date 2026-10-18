/* SPDX-License-Identifier: BSD-2-Clause */
/* Origin: EmberBSD (AI-assisted). */
#include <stdbool.h>
#include <ngspice/sharedspice.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static unsigned failures, errors, exits, before_quit, after_quit;
static int exit_status;

static void
check(bool good, const char *name)
{
	printf("%s: %s\n", good ? "PASS" : "FAIL", name);
	if (!good)
		++failures;
}

static int
send_text(char *text, int ident, void *context)
{
	(void)ident;
	(void)context;
	puts(text);
	if (strstr(text, "Error") || strstr(text, "error"))
		++errors;
	if (strstr(text, "EMBER_BEFORE_QUIT"))
		++before_quit;
	if (strstr(text, "EMBER_AFTER_QUIT"))
		++after_quit;
	return 0;
}

static int
controlled_exit(int status, bool immediate, bool quit, int ident, void *context)
{
	(void)immediate;
	(void)quit;
	(void)ident;
	(void)context;
	++exits;
	exit_status = status;
	return 0;
}

static void
command(const char *text)
{
	char *copy = malloc(strlen(text) + 1);
	if (!copy) {
		fputs("Out of memory\n", stderr);
		exit(2);
	}
	strcpy(copy, text);
	(void)ngSpice_Command(copy);
	free(copy);
}

static void
voltage(const char *name, double expected)
{
	pvector_info vector;
	char node[] = "v(vout)";

	command("op");
	vector = ngGet_Vec_Info(node);
	check(vector && vector->v_length == 1 && vector->v_realdata &&
	    isfinite(vector->v_realdata[0]) &&
	    fabs(vector->v_realdata[0] - expected) < 1e-9, name);
}

static void
divider(void)
{
	char *circuit[] = {
		"EmberBSD divider", "V1 vin 0 DC 10", "R1 vin vout 3k",
		"R2 vout 0 2k", ".end", NULL
	};

	check(ngSpice_Circ(circuit) == 0, "load divider through installed C API");
}

int
main(void)
{
	unsigned previous_errors;
	pvector_info vector;
	char node[] = "v(vout)";
	char *gain[] = {
		"EmberBSD installed XSPICE gain", "V1 vin 0 DC 3",
		"A1 vin vout gain_model", ".model gain_model gain(gain=2)",
		"R1 vout 0 1k", ".end", NULL
	};
	char *invalid[] = {
		"EmberBSD rejected diode", "V1 vin 0 DC 1",
		"D1 vin 0 missing_model", ".end", NULL
	};

	check(ngSpice_nospiceinit() == 0, "disable user init before initialization");
	check(ngSpice_Init(send_text, NULL, controlled_exit, NULL, NULL, NULL,
	    NULL) == 0, "initialize installed shared library");
	command("version");
	command("set num_threads=2");
	divider();
	voltage("10 V / (3k + 2k) divider produces 4 V", 4.0);
	command("alter R2=3k");
	voltage("alter resistor produces 5 V", 5.0);
	command("alter R2=2k");
	command("dc v1 0 10 2");
	vector = ngGet_Vec_Info(node);
	bool sweep = vector && vector->v_length == 6 && vector->v_realdata;
	for (int i = 0; sweep && i < 6; ++i)
		sweep = isfinite(vector->v_realdata[i]) &&
		    fabs(vector->v_realdata[i] - 0.8 * i) < 1e-9;
	check(sweep, "six-point DC sweep has independent expected voltages");
	command("reset");
	voltage("reset reloads retained divider", 4.0);
	check(ngSpice_Circ(gain) == 0, "load installed XSPICE gain model");
	voltage("installed analog code model produces 6 V", 6.0);
	command("setcirc 2");
	voltage("select older circuit preserves borrowed source names", 4.0);
	previous_errors = errors;
	(void)ngSpice_Circ(invalid);
	check(errors > previous_errors, "invalid model reports error callback");
	command("remcirc");
	divider();
	command("reset");
	voltage("reload after rejected circuit and reset", 4.0);
	check(ngSpice_Reset() == 0, "total reset releases circuits and retained deck");
	check(ngSpice_Init(send_text, NULL, controlled_exit, NULL, NULL, NULL,
	    NULL) == 0, "initialize after total reset");
	divider();
	voltage("new session works after reset", 4.0);
	command("echo EMBER_BEFORE_QUIT; quit; echo EMBER_AFTER_QUIT");
	check(before_quit == 1 && after_quit == 0 && exits == 1 &&
	    exit_status == 0, "compound quit stops dispatch and reports controlled exit");
	return failures ? 1 : 0;
}
