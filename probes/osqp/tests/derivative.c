/* SPDX-License-Identifier: MIT */
/* Origin: EmberBSD (AI-assisted), installed public adjoint derivative check. */
#include <osqp.h>
#include <math.h>
#include <stdio.h>

#ifndef OSQP_ENABLE_DERIVATIVES
#error "Adjoint derivative support is required"
#endif
_Static_assert(sizeof(OSQPFloat) == 8, "Double precision required");
_Static_assert(sizeof(OSQPInt) == 8, "64-bit indices required");

static int
check(int condition, const char *message)
{

	if (!condition)
		fprintf(stderr, "FAIL: %s\n", message);
	return condition;
}

static int
check_value(OSQPFloat value, double expected, const char *name)
{

	if (!isfinite(value) || fabs(value - expected) > 1e-7) {
		fprintf(stderr, "FAIL: %s: %.17g differs from %.17g\n",
		    name, (double)value, expected);
		return 0;
	}
	return 1;
}

int
main(void)
{
	OSQPFloat px[1] = { 2 }, ax[1] = { 1 }, q[1] = { -1 };
	OSQPFloat lower[1] = { -10 }, upper[1] = { 10 };
	OSQPFloat dx[1] = { 1 }, dy[1] = { 0 };
	OSQPFloat dpx[1] = { NAN }, dax[1] = { NAN };
	OSQPFloat dq[1] = { NAN }, dl[1] = { NAN }, du[1] = { NAN };
	OSQPInt indices[1] = { 0 }, columns[2] = { 0, 1 };
	OSQPCscMatrix p, a, dp, da;
	OSQPSettings settings;
	OSQPSolver *solver = NULL;
	int result = 1;

	OSQPCscMatrix_set_data(&p, 1, 1, 1, px, indices, columns);
	OSQPCscMatrix_set_data(&a, 1, 1, 1, ax, indices, columns);
	OSQPCscMatrix_set_data(&dp, 1, 1, 1, dpx, indices, columns);
	OSQPCscMatrix_set_data(&da, 1, 1, 1, dax, indices, columns);
	osqp_set_default_settings(&settings);
	settings.verbose = 0;
	settings.eps_abs = settings.eps_rel = 1e-10;
	settings.max_iter = 10000;
	settings.time_limit = 5.0;

	if (!check(osqp_setup(&solver, &p, q, &a, lower, upper, 1, 1,
	    &settings) == OSQP_NO_ERROR, "QP setup failed"))
		goto done;
	if (!check(osqp_solve(solver) == OSQP_NO_ERROR, "QP solve failed"))
		goto done;
	if (!check(solver->info->status_val == OSQP_SOLVED,
	    "QP did not reach an accurate solution"))
		goto done;
	if (!check_value(solver->solution->x[0], 0.5, "primal solution") ||
	    !check_value(solver->solution->y[0], 0.0, "inactive bound dual"))
		goto done;

	/* For inactive bounds, x = -q/P and L = x. */
	if (!check(osqp_adjoint_derivative_compute(solver, dx, dy) ==
	    OSQP_NO_ERROR, "Adjoint derivative computation failed"))
		goto done;
	if (!check(osqp_adjoint_derivative_get_mat(solver, &dp, &da) ==
	    OSQP_NO_ERROR, "Matrix derivative retrieval failed"))
		goto done;
	if (!check(osqp_adjoint_derivative_get_vec(solver, dq, dl, du) ==
	    OSQP_NO_ERROR, "Vector derivative retrieval failed"))
		goto done;
	if (!check_value(dq[0], -0.5, "dL/dq") ||
	    !check_value(dpx[0], -0.25, "dL/dP") ||
	    !check_value(dax[0], 0.0, "dL/dA") ||
	    !check_value(dl[0], 0.0, "dL/dl") ||
	    !check_value(du[0], 0.0, "dL/du"))
		goto done;
	result = 0;

done:
	if (solver != NULL && !check(osqp_cleanup(solver) == OSQP_NO_ERROR,
	    "Solver cleanup failed"))
		result = 1;
	if (result == 0)
		puts("Public adjoint derivatives match the scalar analytic QP: PASS");
	return result;
}
