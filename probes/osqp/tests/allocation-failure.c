/* SPDX-License-Identifier: MIT */
/* Origin: EmberBSD (AI-assisted), bounded QDLDL constructor failure regression. */
#include <sys/resource.h>
#include <sys/wait.h>
#include <osqp.h>
#include "qdldl_interface.h"
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>

static size_t live;
static int scenario, reached, injected;

void *
fault_malloc(size_t size)
{
	void *ptr = malloc(size);

	if (ptr != NULL)
		live++;
	return ptr;
}

void *
fault_calloc(size_t count, size_t size)
{
	void *ptr;
	int point = 0;

	if (count == 1 && size == sizeof(qdldl_solver)) {
		reached = 1;
		point = 1;
	} else if (reached && count == 1 && size == sizeof(OSQPCscMatrix)) {
		point = 2;
	}
	if (scenario != 0 && point == scenario && injected == 0) {
		injected++;
		return NULL;
	}
	ptr = calloc(count, size);
	if (ptr != NULL)
		live++;
	return ptr;
}

void *
fault_realloc(void *ptr, size_t size)
{
	int was_null = ptr == NULL;
	void *next;

	if (size == 0) {
		if (ptr != NULL) {
			live--;
			free(ptr);
		}
		return NULL;
	}
	next = realloc(ptr, size);
	if (next != NULL && was_null)
		live++;
	return next;
}

void
fault_free(void *ptr)
{

	if (ptr != NULL) {
		live--;
		free(ptr);
	}
}

static int
run_case(int kind)
{
	OSQPFloat px[1] = { 2 }, ax[1] = { 1 }, q[1] = { -1 };
	OSQPFloat lower[1] = { -10 }, upper[1] = { 10 };
	OSQPInt rows[1] = { 0 }, columns[2] = { 0, 1 };
	OSQPCscMatrix p, a;
	OSQPSettings settings;
	OSQPSolver *solver = NULL;
	OSQPInt status;
	int ok;

	scenario = kind;
	reached = injected = 0;
	live = 0;
	OSQPCscMatrix_set_data(&p, 1, 1, 1, px, rows, columns);
	OSQPCscMatrix_set_data(&a, 1, 1, 1, ax, rows, columns);
	osqp_set_default_settings(&settings);
	settings.verbose = 0;
	settings.eps_abs = settings.eps_rel = 1e-9;
	status = osqp_setup(&solver, &p, q, &a, lower, upper, 1, 1, &settings);
	if (kind == 0) {
		ok = status == OSQP_NO_ERROR && reached && injected == 0;
		if (ok)
			ok = osqp_solve(solver) == OSQP_NO_ERROR &&
			    solver->info->status_val == OSQP_SOLVED &&
			    isfinite(solver->solution->x[0]) &&
			    fabs(solver->solution->x[0] - 0.5) < 1e-7;
	} else {
		ok = status == OSQP_MEM_ALLOC_ERROR && injected == 1;
	}
	if (solver != NULL && osqp_cleanup(solver) != OSQP_NO_ERROR)
		ok = 0;
	if (live != 0)
		ok = 0;
	fprintf(stderr, "scenario=%d status=%lld injected=%d live=%zu result=%s\n",
	    kind, (long long)status, injected, live, ok ? "PASS" : "FAIL");
	return ok ? 0 : 1;
}

int
main(void)
{
	const struct rlimit no_core = { 0, 0 };
	pid_t child, waited;
	int kind, status, failed = 0;

	if (setrlimit(RLIMIT_CORE, &no_core) != 0)
		return 1;
	for (kind = 0; kind <= 2; kind++) {
		child = fork();
		if (child == -1)
			return 1;
		if (child == 0)
			_exit(run_case(kind));
		waited = waitpid(child, &status, 0);
		if (waited != child || !WIFEXITED(status) || WEXITSTATUS(status) != 0) {
			fprintf(stderr, "scenario=%d child failed, wait status=%d\n", kind, status);
			failed = 1;
		}
	}
	if (!failed)
		puts("QDLDL setup reports two injected allocation failures and preserves normal solves: PASS");
	return failed;
}
