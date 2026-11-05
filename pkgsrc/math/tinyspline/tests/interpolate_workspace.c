// Copyright (c) 2026 EmberBSD contributors
// SPDX-License-Identifier: BSD-3-Clause
/* Check natural interpolation across the Thomas workspace and point block. */
#include <math.h>
#include <stdio.h>

#include "tinyspline.h"

static int
check_points(const tsReal *points, size_t dimension)
{
	tsBSpline spline = ts_bspline_init();
	tsDeBoorNet net = ts_deboornet_init();
	tsStatus status;
	tsReal min, max;
	size_t i, j;
	int result = 1;

	if (ts_bspline_interpolate_cubic_natural(points, 3, dimension,
	    &spline, &status) != TS_SUCCESS) {
		fprintf(stderr, "interpolation failed: %s\n", status.message);
		return 0;
	}
	ts_bspline_domain(&spline, &min, &max);
	for (i = 0; i < 3; i++) {
		tsReal knot = min + (max - min) * (tsReal)i / 2;
		const tsReal *actual;

		if (ts_bspline_eval(&spline, knot, &net, &status) != TS_SUCCESS) {
			fprintf(stderr, "evaluation failed: %s\n", status.message);
			result = 0;
			break;
		}
		actual = ts_deboornet_result_ptr(&net);
		for (j = 0; j < dimension; j++) {
			if (!isfinite(actual[j]) ||
			    fabs(actual[j] - points[i * dimension + j]) > 1e-5) {
				fprintf(stderr,
				    "%zuD point %zu component %zu: got %.9g, expected %.9g\n",
				    dimension, i, j, actual[j], points[i * dimension + j]);
				result = 0;
			}
		}
	}
	ts_deboornet_free(&net);
	ts_bspline_free(&spline);
	return result;
}

int
main(void)
{
	const tsReal points_2d[] = {
		1, 11, 2, 22, 3, 33
	};
	const tsReal points_3d[] = {
		1, 11, 101, 2, 22, 202, 3, 33, 303
	};
	const tsReal points_4d[] = {
		1, 11, 101, 1001,
		2, 22, 202, 2002,
		3, 33, 303, 3003
	};

	if (!check_points(points_2d, 2) || !check_points(points_3d, 3) ||
	    !check_points(points_4d, 4))
		return 1;
	return 0;
}
