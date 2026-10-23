/* SPDX-License-Identifier: BSD-2-Clause */
/* Copyright 2026 The EmberBSD Authors. All rights reserved. */
/* Independent DFT checks for the imported PFFFT API. */
#include "pffft.h"

#include <math.h>
#include <stdio.h>
#include <string.h>

#ifdef NDEBUG
#error "This fixture requires enabled assertions."
#endif
#ifdef PFFFT_SIMD_DISABLE
#error "This fixture must exercise the target SIMD implementation."
#endif

static int
check_value(const char *label, int length, int bin, double actual,
    double expected)
{
	if (!isfinite(actual) || !isfinite(expected) ||
	    fabs(actual - expected) > 0.001 * (1.0 + fabs(expected))) {
		fprintf(stderr, "%s N=%d bin=%d: got %.9g, expected %.9g\n",
		    label, length, bin, actual, expected);
		return 1;
	}
	return 0;
}

static int
check_transform(int length, pffft_transform_t transform)
{
	const int complex_input = transform == PFFFT_COMPLEX;
	const int count = complex_input ? 2 * length : length;
	const size_t bytes = (size_t)count * sizeof(float);
	PFFFT_Setup *setup = pffft_new_setup(length, transform);
	float *input = pffft_aligned_malloc(bytes);
	float *spectrum = pffft_aligned_malloc(bytes);
	float *inverse = pffft_aligned_malloc(bytes);
	float *work = pffft_aligned_malloc(bytes);
	int failed = 0;
	int k, n;

	if (setup == NULL || input == NULL || spectrum == NULL ||
	    inverse == NULL || work == NULL) {
		fprintf(stderr, "PFFFT allocation or setup failed for N=%d\n",
		    length);
		failed = 1;
		goto cleanup;
	}
	for (n = 0; n < count; ++n) {
		input[n] = (float)((n * 17) % 23 - 11) / 8.0f;
	}
	memset(spectrum, 0, bytes);
	memset(inverse, 0, bytes);
	memset(work, 0, bytes);
	pffft_transform_ordered(setup, input, spectrum, work, PFFFT_FORWARD);

	for (k = 0; k < (complex_input ? length : length / 2 + 1); ++k) {
		double real = 0.0, imaginary = 0.0;
		for (n = 0; n < length; ++n) {
			const double angle =
			    -2.0 * 3.14159265358979323846 * k * n / length;
			const double input_real =
			    input[complex_input ? 2 * n : n];
			const double input_imaginary =
			    complex_input ? input[2 * n + 1] : 0.0;
			real += input_real * cos(angle) -
			    input_imaginary * sin(angle);
			imaginary += input_real * sin(angle) +
			    input_imaginary * cos(angle);
		}
		if (!complex_input && (k == 0 || k == length / 2)) {
			failed |= check_value("real endpoint", length, k,
			    spectrum[k == 0 ? 0 : 1], real);
		} else {
			failed |= check_value(
			    "real", length, k, spectrum[2 * k], real);
			failed |= check_value("imaginary", length, k,
			    spectrum[2 * k + 1], imaginary);
		}
	}

	pffft_transform_ordered(setup, spectrum, inverse, work, PFFFT_BACKWARD);
	for (n = 0; n < count; ++n) {
		failed |= check_value(
		    "inverse", length, n, inverse[n] / length, input[n]);
	}

cleanup:
	pffft_aligned_free(work);
	pffft_aligned_free(inverse);
	pffft_aligned_free(spectrum);
	pffft_aligned_free(input);
	if (setup != NULL) {
		pffft_destroy_setup(setup);
	}
	return failed;
}

int
main(void)
{
	static const int lengths[] = {16, 48, 80};
	int failed = 0;
	size_t i;

	validate_pffft_simd();
	for (i = 0; i < sizeof(lengths) / sizeof(lengths[0]); ++i) {
		failed |= check_transform(lengths[i], PFFFT_COMPLEX);
		failed |= check_transform(2 * lengths[i], PFFFT_REAL);
	}
	if (failed) {
		return 1;
	}
	printf(
	    "PFFFT PASS: enabled SIMD assertions, 6 forward DFT and inverse cases; SIMD=%d\n",
	    pffft_simd_size());
	return 0;
}
