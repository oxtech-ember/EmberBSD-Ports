/* SPDX-License-Identifier: BSD-2-Clause
 * Origin: EmberBSD (AI-assisted). Shared-library streaming and duration checks.
 */
#include <assert.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sonic.h>

static short input[48000];
static short output[50000];

static void
run(float speed)
{
	sonicStream stream = sonicCreateStream(48000, 1);
	assert(stream != NULL);
	sonicSetSpeed(stream, speed);
	for (int i = 0; i < 48000; i += 480)
		assert(sonicWriteShortToStream(stream, input + i, 480) != 0);
	assert(sonicFlushStream(stream) != 0);
	int available = sonicSamplesAvailable(stream);
	assert(available > 0 && available <= 50000);
	int count = sonicReadShortFromStream(stream, output, 50000);
	assert(count == available && sonicSamplesAvailable(stream) == 0);
	assert(sonicReadShortFromStream(stream, output + count, 0) == 0);
	if (speed == 1.0f) {
		assert(count == 48000);
		assert(memcmp(input, output, sizeof(input)) == 0);
	} else {
		assert(count >= 23520 && count <= 24480);
		int crossings = 0;
		long long energy = 0;
		for (int i = 1; i < count; ++i) {
			if (output[i - 1] <= 0 && output[i] > 0)
				++crossings;
			energy += (long long)output[i] * output[i];
		}
		double frequency = (double)crossings * 48000 / count;
		assert(frequency > 420 && frequency < 460);
		assert(energy / count > 1000000);
	}
	sonicDestroyStream(stream);
	printf("PASS: speed %.1f, %d samples, drained stream\n", speed, count);
}

int
main(void)
{
	for (int i = 0; i < 48000; ++i)
		input[i] = (short)(12000 * sin(2 * 3.141592653589793 * 440 * i / 48000));
	run(1.0f);
	run(2.0f);
	return 0;
}
