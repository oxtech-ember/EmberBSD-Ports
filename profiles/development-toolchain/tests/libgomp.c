/* SPDX-License-Identifier: BSD-2-Clause */
/* Origin: EmberBSD; AI-assisted OpenMP runtime contract. */
#define _GNU_SOURCE

#include <sys/types.h>

#include <link.h>
#include <omp.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

#define WORKERS 4
#define ITERATIONS 10000
#define TASKS 256

struct provider {
	const char *expected;
	unsigned int count;
	unsigned int mismatches;
};

static _Thread_local unsigned int worker_token;

/* dl_iterate_phdr requires this exact non-const callback parameter type. */
static int
/* cppcheck-suppress constParameterCallback */
check_provider(struct dl_phdr_info *info, size_t size, void *arg)
{
	struct provider *provider = arg;
	const char *name, *base;

	(void)size;
	name = info->dlpi_name;
	base = strrchr(name, '/');
	base = base != NULL ? base + 1 : name;
	if (strncmp(base, "libgomp.so.", 11) != 0)
		return 0;
	provider->count++;
	if (strcmp(name, provider->expected) != 0) {
		fprintf(stderr, "Unexpected libgomp provider: %s\n", name);
		provider->mismatches++;
	}
	return 0;
}

int
main(int argc, char **argv)
{
	struct provider provider;
	omp_lock_t lock;
	uintptr_t addresses[WORKERS] = { 0 };
	long long sum = 0, task_sum = 0;
	double half_sum = 0.0;
	unsigned int failures = 0, task_failures = 0, task_count = 0;
	int workers = 0, i, j;

	if (argc != 2 || argv[1][0] != '/') {
		fprintf(stderr, "Usage: %s /absolute/loaded/libgomp.so.VERSION\n",
		    argv[0]);
		return 2;
	}
	provider = (struct provider){ argv[1], 0, 0 };
	(void)dl_iterate_phdr(check_provider, &provider);
	if (provider.count != 1 || provider.mismatches != 0) {
		fprintf(stderr, "Expected exactly one matching libgomp provider\n");
		return 1;
	}
	omp_set_dynamic(0);
	omp_init_lock(&lock);
#pragma omp parallel num_threads(WORKERS) default(none) \
    shared(addresses, workers, lock, task_sum, task_count, task_failures) \
    reduction(+:sum, half_sum, failures)
	{
		int thread = omp_get_thread_num();

		worker_token = 0x100U + (unsigned int)thread;
		addresses[thread] = (uintptr_t)&worker_token;
#pragma omp single
		workers = omp_get_num_threads();
#pragma omp barrier
		if (worker_token != 0x100U + (unsigned int)thread)
			failures++;
#pragma omp for schedule(static)
		for (int item = 1; item <= ITERATIONS; item++) {
			sum += item;
			half_sum += 0.5 * item;
		}
#pragma omp single
		{
			for (int item = 1; item <= TASKS; item++) {
#pragma omp task firstprivate(item) \
    shared(lock, task_sum, task_count, task_failures)
				{
					unsigned int expected = 0x100U +
					    (unsigned int)omp_get_thread_num();

					omp_set_lock(&lock);
					task_sum += item;
					task_count++;
					if (worker_token != expected)
						task_failures++;
					omp_unset_lock(&lock);
				}
			}
#pragma omp taskwait
		}
		if (worker_token != 0x100U + (unsigned int)thread)
			failures++;
	}
	omp_destroy_lock(&lock);
	for (i = 0; i < WORKERS; i++) {
		if (addresses[i] == 0)
			failures++;
		for (j = i + 1; j < WORKERS; j++) {
			if (addresses[i] == addresses[j])
				failures++;
		}
	}
	if (omp_pause_resource_all(omp_pause_hard) != 0) {
		fprintf(stderr, "OpenMP worker shutdown failed\n");
		return 1;
	}
	if (workers != WORKERS || sum != 50005000 ||
	    half_sum != 25002500.0 || task_sum != 32896 ||
	    task_count != TASKS || failures != 0 || task_failures != 0) {
		fprintf(stderr, "OpenMP reduction/tasks/lock/TLS contract failed\n");
		return 1;
	}
	printf("PASS OpenMP: %d workers, %d reductions, %d locked tasks, "
	    "distinct worker TLS; provider=%s\n", WORKERS, ITERATIONS, TASKS,
	    provider.expected);
	return 0;
}
