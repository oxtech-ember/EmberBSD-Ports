#include <pffft/pffft.h>
#include <stdio.h>

int
main(void)
{
	float *a = pffft_aligned_malloc(132 * sizeof(float));
	float *b = pffft_aligned_malloc(132 * sizeof(float));
	float *work = pffft_aligned_malloc(128 * sizeof(float));
	PFFFT_Setup *setup = pffft_new_setup(128, PFFFT_REAL);
	int i;

	if (a == NULL || b == NULL || work == NULL || setup == NULL)
		return 1;
	for (i = 0; i < 128; i++)
		a[i + 1] = i == 0 ? 1.0f : 0.0f;
	pffft_transform_ordered(setup, a + 1, b + 1, work, PFFFT_FORWARD);
	pffft_destroy_setup(setup);
	pffft_aligned_free(a);
	pffft_aligned_free(b);
	pffft_aligned_free(work);
	puts("unaligned FFT unexpectedly succeeded");
	return 1;
}
