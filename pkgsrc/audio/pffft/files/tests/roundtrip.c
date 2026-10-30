#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <pffft/pffft.h>

int
main(void)
{
	const int n = 128;
	float *input = pffft_aligned_malloc(n * sizeof(*input));
	float *freq = pffft_aligned_malloc(n * sizeof(*freq));
	float *output = pffft_aligned_malloc(n * sizeof(*output));
	float *work = pffft_aligned_malloc(n * sizeof(*work));
	PFFFT_Setup *setup = pffft_new_setup(n, PFFFT_REAL);
	int i;

	if (!input || !freq || !output || !work || !setup)
		return 1;
	for (i = 0; i < n; i++)
		input[i] = 0.25f + sinf((float)(2.0 * 3.141592653589793 * 7 * i / n));
	pffft_transform_ordered(setup, input, freq, work, PFFFT_FORWARD);
	if (fabsf(freq[0] - 32.0f) > 0.001f || fabsf(freq[15] + 64.0f) > 0.001f)
		return 2;
	pffft_transform_ordered(setup, freq, output, work, PFFFT_BACKWARD);
	for (i = 0; i < n; i++)
		if (fabsf(output[i] / n - input[i]) > 0.0001f)
			return 3;
	pffft_destroy_setup(setup);
	pffft_aligned_free(input);
	pffft_aligned_free(freq);
	pffft_aligned_free(output);
	pffft_aligned_free(work);
	puts("pffft ordered spectrum and roundtrip PASS");
	return 0;
}
