/* Origin: EmberBSD; AI-assisted foreign ELF ABI probe. */
/* SPDX-License-Identifier: BSD-2-Clause */

#define _POSIX_C_SOURCE 200809L

#include <sys/types.h>
#include <dlfcn.h>
#include <errno.h>
#include <pthread.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

typedef int (*get_fn)(void);
typedef void (*set_fn)(int);

struct worker {
	get_fn get;
	set_fn set;
	pthread_barrier_t *barrier;
	int value;
	int failure;
};

int probe_binding_marker(void);

int
probe_binding_marker(void)
{
	return 11;
}

static int
barrier_wait(pthread_barrier_t *barrier)
{
	int error = pthread_barrier_wait(barrier);

	return error == 0 || error == PTHREAD_BARRIER_SERIAL_THREAD ? 0 : error;
}

static void *
tls_worker(void *arg)
{
	struct worker *worker = arg;

	/* First announce arrival; then wait for dlopen and symbol assignment. */
	if (barrier_wait(worker->barrier) != 0 ||
	    barrier_wait(worker->barrier) != 0)
		_exit(73);
	if (worker->get() != 7)
		worker->failure = 1;
	worker->set(worker->value);
	if (barrier_wait(worker->barrier) != 0)
		worker->failure = 1;
	if (worker->get() != worker->value)
		worker->failure = 1;
	if (barrier_wait(worker->barrier) != 0)
		worker->failure = 1;
	return NULL;
}

static void
start_workers(pthread_t threads[2], struct worker workers[2])
{
	for (unsigned int i = 0; i < 2; i++) {
		if (pthread_create(&threads[i], NULL, tls_worker, &workers[i]) != 0) {
			/* A partially started barrier cannot be joined safely. */
			fprintf(stderr, "pthread_create failed\n");
			_exit(73);
		}
	}
}

static int
test_tls(const char *path, int preexisting)
{
	void *handle;
	get_fn get;
	set_fn set;
	pthread_t threads[2];
	pthread_barrier_t barrier;
	struct worker workers[2];
	int failures = 0;

	if (pthread_barrier_init(&barrier, NULL, 3) != 0)
		return 73;
	for (unsigned int i = 0; i < 2; i++)
		workers[i] = (struct worker){NULL, NULL, &barrier, 100 + (int)i, 0};
	if (preexisting) {
		start_workers(threads, workers);
		/* Both workers have run before the DSO is loaded. */
		if (barrier_wait(&barrier) != 0)
			_exit(73);
	}
	handle = dlopen(path, RTLD_NOW | RTLD_LOCAL);
	if (handle == NULL) {
		fprintf(stderr, "dlopen: %s\n", dlerror());
		_exit(71);
	}
	get = (get_fn)dlsym(handle, "probe_tls_get");
	set = (set_fn)dlsym(handle, "probe_tls_set");
	if (get == NULL || set == NULL) {
		fprintf(stderr, "TLS symbols missing: %s\n", dlerror());
		_exit(72);
	}
	if (get() != 7)
		failures++;
	set(21);
	for (unsigned int i = 0; i < 2; i++) {
		workers[i].get = get;
		workers[i].set = set;
	}
	if (!preexisting) {
		start_workers(threads, workers);
		if (barrier_wait(&barrier) != 0)
			_exit(73);
	}
	/* Publish symbol pointers before either worker can access them. */
	if (barrier_wait(&barrier) != 0)
		_exit(73);
	if (barrier_wait(&barrier) != 0)
		failures++;
	if (get() != 21)
		failures++;
	if (barrier_wait(&barrier) != 0)
		failures++;
	for (unsigned int i = 0; i < 2; i++) {
		if (pthread_join(threads[i], NULL) != 0) {
			fprintf(stderr, "pthread_join failed\n");
			_exit(73);
		}
		failures += workers[i].failure;
	}
	if (get() != 21)
		failures++;
	if (pthread_barrier_destroy(&barrier) != 0)
		failures++;
	printf("TLS preexisting=%d failures=%d main=%d expected_main=21 "
	    "workers=100,101\n", preexisting, failures, get());
	if (dlclose(handle) != 0)
		return 74;
	return failures == 0 ? 0 : 65;
}

int
main(int argc, char **argv)
{
	void *handle;
	int result;

	if (geteuid() == 0)
		return 77;
	if (argc < 3 || (strcmp(argv[1], "tls") != 0 &&
	    strcmp(argv[1], "tls-preexisting") != 0 &&
	    strcmp(argv[1], "binding") != 0) ||
	    (strcmp(argv[1], "binding") != 0 && argc != 3) ||
	    (strcmp(argv[1], "binding") == 0 && argc != 4))
		return 64;
	if (strcmp(argv[1], "binding") != 0)
		return test_tls(argv[2], strcmp(argv[1], "tls-preexisting") == 0);
	handle = dlopen(argv[2], RTLD_NOW | RTLD_LOCAL);
	if (handle == NULL) {
		fprintf(stderr, "dlopen: %s\n", dlerror());
		return 71;
	}
	{
		get_fn consumer = (get_fn)dlsym(handle, "probe_consumer");
		char *end;
		long expected;
		int actual;

		if (consumer == NULL) {
			result = 72;
			goto done;
		}
		errno = 0;
		expected = strtol(argv[3], &end, 10);
		if (errno || end == argv[3] || *end || expected < 0 || expected > 255) {
			result = 64;
			goto done;
		}
		actual = consumer();
		printf("BINDING actual=%d expected=%ld\n", actual, expected);
		result = actual == expected ? 0 : 65;
	}
done:
	if (dlclose(handle) != 0) {
		fprintf(stderr, "dlclose: %s\n", dlerror());
		return 74;
	}
	return result;
}
