/* SPDX-License-Identifier: Apache-2.0 */
/* Test the real native backend without opening a USB device. */
#include <assert.h>
#include <errno.h>
#include <fcntl.h>
#include <limits.h>
#include <pthread.h>
#include <sched.h>
#include <signal.h>
#include <stdarg.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <sys/wait.h>
#include <time.h>
#include <unistd.h>

#ifndef __CTASSERT
#define __CTASSERT(expr) _Static_assert((expr), #expr)
#endif
#ifndef __packed
#define __packed __attribute__((__packed__))
#endif

static int test_open(const char *, int, ...);
static int test_close(int);
static int test_ioctl(int, unsigned long, ...);
static int test_pthread_create(pthread_t *, const pthread_attr_t *,
    void *(*)(void *), void *);
static int test_pthread_join(pthread_t, void **);
static int test_sched_yield(void);
static int test_nanosleep(const struct timespec *, struct timespec *);

/* NetBSD maps these names to libc thread entry points. */
#pragma push_macro("pthread_join")
#pragma push_macro("sched_yield")
#undef pthread_join
#undef sched_yield
#define open test_open
#define close test_close
#define ioctl test_ioctl
#define pthread_create test_pthread_create
#define pthread_join test_pthread_join
#define sched_yield test_sched_yield
#define nanosleep test_nanosleep
#define main gaster_main
#include "../gaster.c"
#undef main
#undef nanosleep
#undef sched_yield
#undef pthread_join
#pragma pop_macro("sched_yield")
#pragma pop_macro("pthread_join")
#undef pthread_create
#undef ioctl
#undef close
#undef open

static pthread_mutex_t gate_mutex = PTHREAD_MUTEX_INITIALIZER;
static pthread_cond_t gate_cond = PTHREAD_COND_INITIALIZER;
static bool release_worker, worker_started, aborted, early_abort;
static bool async_request, delay_worker, fail_create, fail_join;
static int timeout_ms, request_error = ECANCELED;
static unsigned port_resets;
static unsigned failed_scans, scan_index, open_calls, sleep_calls;
static unsigned expected_poll_ms;
static void *(*worker_fn)(void *);
static void *worker_arg;

static int
test_open(const char *path, int flags, ...)
{

	open_calls++;
	if (failed_scans != 0) {
		char expected_node[16];

		snprintf(expected_node, sizeof(expected_node), "/dev/ugen%u.00",
		    scan_index);
		assert(strcmp(path, expected_node) == 0);
		assert(flags == O_RDWR);
		if (++scan_index == 32) {
			scan_index = 0;
			failed_scans--;
		}
		errno = ENOENT;
		return -1;
	}
	assert(strcmp(path, "/dev/ugen0.00") == 0 ||
	    strcmp(path, "/dev/usb0") == 0);
	assert(flags == O_RDWR);
	return 42;
}

static int
test_nanosleep(const struct timespec *request, struct timespec *remaining)
{

	if (expected_poll_ms == 0)
		return nanosleep(request, remaining);
	assert(remaining == NULL);
	assert(request->tv_sec == expected_poll_ms / 1000);
	assert(request->tv_nsec == (expected_poll_ms % 1000) * 1000000L);
	sleep_calls++;
	return 0;
}

static int
test_close(int fd)
{

	assert(fd == 42);
	return 0;
}

static int
test_ioctl(int fd, unsigned long operation, ...)
{
	struct usb_device_info *di;
	struct usb_ctl_request *req;
	va_list ap;
	void *arg;

	assert(fd == 42);
	if (operation == USB_ABORT_REQUEST) {
		assert(pthread_mutex_lock(&gate_mutex) == 0);
		early_abort = !worker_started;
		aborted = true;
		/* Release the delayed worker even if the backend aborted too soon. */
		release_worker = true;
		assert(pthread_cond_broadcast(&gate_cond) == 0);
		assert(pthread_mutex_unlock(&gate_mutex) == 0);
		return 0;
	}
	va_start(ap, operation);
	arg = va_arg(ap, void *);
	va_end(ap);
	if (operation == USB_GET_DEVICEINFO) {
		di = arg;
		memset(di, 0, sizeof(*di));
		di->udi_vendorNo = APPLE_VID;
		di->udi_productNo = DFU_MODE_PID;
		return 0;
	}
	if (operation == USB_SET_CONFIG) {
		assert(*(int *)arg == 1);
		return 0;
	}
	if (operation == USB_SET_TIMEOUT) {
		timeout_ms = *(int *)arg;
		return 0;
	}
	if (operation == USB_REQUEST) {
		req = arg;
		if (req->ucr_request.bmRequestType == 0xa0 &&
		    req->ucr_request.bRequest == 6) {
			/* Root hub descriptor with one port. */
			((unsigned char *)req->ucr_data)[2] = 1;
		} else if (req->ucr_request.bmRequestType == 0xa3 &&
		    req->ucr_request.bRequest == 0) {
			/* Port 1 is connected. */
			assert(UGETW(req->ucr_request.wIndex) == 1);
			((unsigned char *)req->ucr_data)[0] = 1;
		} else {
			assert(req->ucr_request.bmRequestType == 0x23);
			assert(req->ucr_request.bRequest == 3);
			assert(UGETW(req->ucr_request.wValue) == 4);
			assert(UGETW(req->ucr_request.wIndex) == 1);
			port_resets++;
		}
		return 0;
	}
	assert(operation == USB_DO_REQUEST);
	req = arg;
	assert(req->ucr_request.bRequest == DFU_GET_STATUS);
	assert(UGETW(req->ucr_request.wLength) == 6);
	if (!async_request) {
		/* Model a 25 ms response with the configured millisecond timeout. */
		if (timeout_ms < 25) {
			errno = ETIMEDOUT;
			return -1;
		}
		req->ucr_actlen = 6;
		return 0;
	}
	assert(pthread_mutex_lock(&gate_mutex) == 0);
	while (!aborted)
		assert(pthread_cond_wait(&gate_cond, &gate_mutex) == 0);
	assert(pthread_mutex_unlock(&gate_mutex) == 0);
	if (request_error == 0) {
		req->ucr_actlen = 6;
		return 0;
	}
	errno = request_error;
	return -1;
}

static void *
delayed_worker(void *arg)
{

	(void)arg;
	assert(pthread_mutex_lock(&gate_mutex) == 0);
	while (delay_worker && !release_worker)
		assert(pthread_cond_wait(&gate_cond, &gate_mutex) == 0);
	worker_started = true;
	assert(pthread_mutex_unlock(&gate_mutex) == 0);
	return worker_fn(worker_arg);
}

static int
test_pthread_create(pthread_t *thread, const pthread_attr_t *attr,
    void *(*fn)(void *), void *arg)
{

	if (fail_create)
		return EAGAIN;
	worker_fn = fn;
	worker_arg = arg;
	return pthread_create(thread, attr, delayed_worker, NULL);
}

static int
test_pthread_join(pthread_t thread, void **result)
{
	int error;

	error = pthread_join(thread, result);
	return fail_join ? EINVAL : error;
}

static int
test_sched_yield(void)
{

	assert(pthread_mutex_lock(&gate_mutex) == 0);
	release_worker = true;
	assert(pthread_cond_broadcast(&gate_cond) == 0);
	assert(pthread_mutex_unlock(&gate_mutex) == 0);
	return sched_yield();
}

static void
check_async(const usb_handle_t *handle)
{
	transfer_ret_t result = { USB_TRANSFER_OK, 99 };
	unsigned char data[6];
	bool ok;

	async_request = true;
	ok = send_usb_control_request_async(handle, 0xa1, DFU_GET_STATUS,
	    0, 0, data, sizeof(data), 1, &result);
	if (fail_create) {
		assert(!ok);
		assert(gaster_dbg_async_errno == EAGAIN);
		assert(result.ret == USB_TRANSFER_ERROR && result.sz == 0);
		assert(!worker_started && !aborted);
		return;
	}
	assert(ok);
	assert(!early_abort);
	assert(gaster_dbg_async_errno == request_error);
	assert(result.sz == (request_error == 0 ? 6 : 0));
	assert(result.ret == (request_error == 0 ? USB_TRANSFER_OK :
	    request_error == EPIPE ? USB_TRANSFER_STALL : USB_TRANSFER_ERROR));
}

static void
check_timeout(const char *setting, int expected_timeout_ms)
{
	char *args[] = { "gaster-test", NULL };
	usb_handle_t handle;
	transfer_ret_t result;
	unsigned char data[6];

	if (setting == NULL)
		assert(unsetenv("USB_TIMEOUT") == 0);
	else
		assert(setenv("USB_TIMEOUT", setting, 1) == 0);
	/* Exercise the real CLI default and environment parser without USB work. */
	assert(gaster_main(1, args) == EXIT_FAILURE);
	init_usb_handle(&handle, APPLE_VID, DFU_MODE_PID);
	assert(wait_usb_handle(&handle, NULL, NULL));
	assert(timeout_ms == expected_timeout_ms);
	assert(send_usb_control_request(&handle, 0xa1, DFU_GET_STATUS,
	    0, 0, data, sizeof(data), &result));
	if (expected_timeout_ms == 5) {
		assert(result.ret == USB_TRANSFER_ERROR && result.sz == 0);
		assert(gaster_dbg_sync_errno == ETIMEDOUT);
	} else {
		assert(result.ret == USB_TRANSFER_OK && result.sz == 6);
		assert(gaster_dbg_sync_errno == 0);
	}
	close_usb_handle(&handle);
	assert(handle.fd == -1);
}

static void
check_poll(const char *timeout_setting, const char *poll_setting,
    unsigned interval_ms, int request_timeout_ms)
{

	if (poll_setting == NULL)
		assert(unsetenv("USB_POLL_INTERVAL_MS") == 0);
	else
		assert(setenv("USB_POLL_INTERVAL_MS", poll_setting, 1) == 0);
	failed_scans = 3;
	scan_index = open_calls = sleep_calls = 0;
	expected_poll_ms = interval_ms;
	check_timeout(timeout_setting, request_timeout_ms);
	assert(failed_scans == 0 && scan_index == 0);
	assert(open_calls == 3 * 32 + 1 && sleep_calls == 3);
}

static void
check_invalid_poll(void)
{
	static const char *settings[] = {
		"", "0", "1001", "-1", "+10", " 10", "10 ", "10ms", "1.0",
		"999999999999999999999999999999999999999999999999999"
	};
	char *args[] = { "gaster-test", NULL };

	for (size_t i = 0; i < sizeof(settings) / sizeof(settings[0]); i++) {
		char diagnostic[256];
		int fds[2], saved_stderr;
		ssize_t count;

		assert(setenv("USB_POLL_INTERVAL_MS", settings[i], 1) == 0);
		assert(pipe(fds) == 0);
		saved_stderr = dup(STDERR_FILENO);
		assert(saved_stderr >= 0);
		assert(dup2(fds[1], STDERR_FILENO) == STDERR_FILENO);
		assert(close(fds[1]) == 0);
		assert(gaster_main(1, args) == EXIT_FAILURE);
		assert(fflush(stderr) == 0);
		assert(dup2(saved_stderr, STDERR_FILENO) == STDERR_FILENO);
		assert(close(saved_stderr) == 0);
		count = read(fds[0], diagnostic, sizeof(diagnostic) - 1);
		assert(close(fds[0]) == 0);
		assert(count > 0);
		diagnostic[count] = '\0';
		assert(strstr(diagnostic, "USB_POLL_INTERVAL_MS") != NULL);
		assert(strstr(diagnostic, "1..1000") != NULL);
		assert(open_calls == 0);
	}
}

static void
check_stage_resets(bool skip_spray, bool skip_all)
{
	static const struct {
		enum checkm8_stage stage;
		bool success;
		unsigned opt_in_resets;
	} cases[] = {
		{ STAGE_RESET, false, 1 },
		{ STAGE_RESET, true, 1 },
		{ STAGE_SETUP, false, 1 },
		{ STAGE_SETUP, true, 1 },
		{ STAGE_SPRAY, false, 1 },
		{ STAGE_SPRAY, true, 0 },
		{ STAGE_PATCH, false, 1 },
		{ STAGE_PATCH, true, 1 }
	};
	char *args[] = { "gaster-test", NULL };
	usb_handle_t handle;
	size_t i;

	if (skip_spray)
		assert(setenv("GASTER_SKIP_SPRAY_RESET", "1", 1) == 0);
	else
		assert(unsetenv("GASTER_SKIP_SPRAY_RESET") == 0);
	if (skip_all)
		assert(setenv("GASTER_SKIP_RESET", "1", 1) == 0);
	else
		assert(unsetenv("GASTER_SKIP_RESET") == 0);
	assert(gaster_main(1, args) == EXIT_FAILURE);
	init_usb_handle(&handle, APPLE_VID, DFU_MODE_PID);
	handle.fd = 42;
	for (i = 0; i < sizeof(cases) / sizeof(cases[0]); i++) {
		const unsigned expected = skip_all ? 0 :
		    skip_spray ? cases[i].opt_in_resets : 1;

		port_resets = 0;
		reset_usb_handle_after_stage(&handle, cases[i].stage,
		    cases[i].success);
		assert(port_resets == expected);
	}
}

int
main(int argc, char **argv)
{
	usb_handle_t handle;
	transfer_ret_t result;
	unsigned char data[6];
	char timeout_setting[32];
	pid_t child;
	int status;

	assert(argc == 2);
	assert(unsetenv("USB_POLL_INTERVAL_MS") == 0);
	init_usb_handle(&handle, APPLE_VID, DFU_MODE_PID);
	if (strcmp(argv[1], "timeout") == 0) {
		check_timeout("1000", 1000);
	} else if (strcmp(argv[1], "timeout-default") == 0) {
		check_timeout(NULL, 5);
	} else if (strcmp(argv[1], "timeout-limit") == 0) {
		snprintf(timeout_setting, sizeof(timeout_setting), "%u", (unsigned)INT_MAX);
		check_timeout(timeout_setting, INT_MAX);
	} else if (strcmp(argv[1], "timeout-overflow") == 0) {
		snprintf(timeout_setting, sizeof(timeout_setting), "%u", (unsigned)INT_MAX + 1U);
		check_timeout(timeout_setting, INT_MAX);
	} else if (strcmp(argv[1], "timeout-max") == 0) {
		snprintf(timeout_setting, sizeof(timeout_setting), "%u", UINT_MAX);
		check_timeout(timeout_setting, INT_MAX);
	} else if (strcmp(argv[1], "poll-default") == 0) {
		check_poll("1000", NULL, 1000, 1000);
		check_poll(NULL, NULL, 5, 5);
	} else if (strcmp(argv[1], "poll-opt-in") == 0) {
		check_poll("1000", "10", 10, 1000);
	} else if (strcmp(argv[1], "poll-bounds") == 0) {
		check_poll("1000", "1", 1, 1000);
		check_poll("1000", "1000", 1000, 1000);
	} else if (strcmp(argv[1], "poll-invalid") == 0) {
		check_invalid_poll();
	} else if (strcmp(argv[1], "spray-reset-default") == 0) {
		check_stage_resets(false, false);
	} else if (strcmp(argv[1], "spray-reset-opt-in") == 0) {
		check_stage_resets(true, false);
	} else if (strcmp(argv[1], "skip-reset-legacy") == 0) {
		check_stage_resets(false, true);
		check_stage_resets(true, true);
	} else {
		handle.fd = 42;
		delay_worker = true;
		if (strcmp(argv[1], "create-error") == 0) {
			fail_create = true;
		} else if (strcmp(argv[1], "join-error") == 0) {
			child = fork();
			assert(child >= 0);
			if (child == 0) {
				fail_join = true;
				async_request = true;
				(void)send_usb_control_request_async(&handle, 0xa1,
				    DFU_GET_STATUS, 0, 0, data, sizeof(data), 1, &result);
				_exit(1);
			}
			assert(waitpid(child, &status, 0) == child);
			assert(WIFSIGNALED(status) && WTERMSIG(status) == SIGABRT);
			puts("PASS join-error");
			return 0;
		} else if (strcmp(argv[1], "success") == 0) {
			request_error = 0;
		} else if (strcmp(argv[1], "stall") == 0) {
			request_error = EPIPE;
		} else {
			assert(strcmp(argv[1], "start") == 0);
		}
		check_async(&handle);
	}
	printf("PASS %s\n", argv[1]);
	return 0;
}
