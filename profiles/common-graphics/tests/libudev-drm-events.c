/* SPDX-License-Identifier: BSD-2-Clause */
/* Real native parser, path classification and KWin's subsystem filter. */
#include <sys/socket.h>
#include <stdio.h>
#include <unistd.h>
#include "udev-utils.c"
#include "libudev-contract-stubs.h"
#include "ndevd.h"
#define udev_dev_monitor native_udev_dev_monitor
#include "native-monitor.inc"
#undef udev_dev_monitor

#ifndef TEST_PACKET_SOCKET
#define TEST_PACKET_SOCKET SOCK_SEQPACKET
#endif

#define CHECK(x, text) do { if (!(x)) { \
	fprintf(stderr, "FAIL %s\n", text); return (1); } } while (0)

static int
parse(const void *packet, size_t length, char *path, size_t capacity)
{
#ifdef BASELINE
	struct ndevd_msg msg;

	(void)length;
	memcpy(&msg, packet, sizeof(msg));
	return (parse_ndevd_message(msg, path, capacity));
#else
	return (parse_ndevd_message(packet, length, path, capacity));
#endif
}

static struct ndevd_msg
message(const char *event, const char *device)
{
	struct ndevd_msg msg = {0};

	strlcpy(msg.event, event, sizeof(msg.event));
	strlcpy(msg.device, device, sizeof(msg.device));
	strlcpy(msg.parent, "bcmkms0", sizeof(msg.parent));
	return (msg);
}

static int
check_filter(void)
{
	static const char * const nodes[] = {
		"/dev/dri/card0", "/dev/dri/card42", "/dev/dri/renderD128"
	};
	struct udev_filter_head filters;
	size_t i;
	int result = 0;

	udev_filter_init(&filters);
	if (udev_filter_add(&filters, UDEV_FILTER_TYPE_SUBSYSTEM,
	    0, "drm", "drm_minor") != 0)
		abort();
	for (i = 0; i < nitems(nodes); i++) {
		if (!udev_filter_match(NULL, &filters, nodes[i])) {
			fprintf(stderr, "FAIL drm_minor filter path=%s\n", nodes[i]);
			result = 1;
		}
	}
	udev_filter_free(&filters);
	return (result);
}

int
main(int argc, char **argv)
{
	static const char * const invalid[] = {
		"dri/card", "dri/card-1", "dri/card+1", "dri/card0x",
		"dri/card0/child", "dri/card0\n", "dri/card0/../card1",
		"dri/renderD128", "../dri/card0", "/dev/dri/card0", "ukbd0"
	};
	struct ndevd_msg msg;
	char path[256], before[256], byte;
	unsigned char packet[sizeof(msg) + 3];
	size_t i;
	int sockets[2], action;

	CHECK(sizeof(msg) == 195, "ndevd wire size");
	if (argc == 2 && strcmp(argv[1], "filter") == 0)
		return (check_filter());
	msg = message("device-change", "dri/card42");
	CHECK(parse(&msg, sizeof(msg), path, sizeof(path)) == UD_ACTION_HOTPLUG,
	    "native primary change discarded");
	CHECK(strcmp(path, "/dev/dri/card42") == 0, "wrong primary identity");
	if (argc == 2 && strcmp(argv[1], "change") == 0)
		return (0);
	CHECK(check_filter() == 0, "KWin filter");
	for (i = 0; i < nitems(invalid); i++) {
		msg = message("device-change", invalid[i]);
		CHECK(parse(&msg, sizeof(msg), path, sizeof(path)) == UD_ACTION_NONE,
		    "invalid change path accepted");
	}
	msg = message("device-attach", "input/event0");
	CHECK(parse(&msg, sizeof(msg), path, sizeof(path)) == UD_ACTION_ADD &&
	    strcmp(path, "/dev/input/event0") == 0, "attach regressed");
	msg = message("device-detach", "input/event0");
	CHECK(parse(&msg, sizeof(msg), path, sizeof(path)) == UD_ACTION_REMOVE,
	    "detach regressed");
	msg = message("unknown", "dri/card0");
	CHECK(parse(&msg, sizeof(msg), path, sizeof(path)) == UD_ACTION_NONE,
	    "unknown event accepted");
	msg = message("device-change", "dri/card0");
	for (i = 0; i < sizeof(msg); i++) {
		CHECK(parse(&msg, i, path, sizeof(path)) == UD_ACTION_NONE,
		    "short packet accepted");
	}
	CHECK(parse(&msg, sizeof(msg) + 1, path, sizeof(path)) == UD_ACTION_NONE,
	    "oversize packet accepted");
	for (i = 0; i < 3; i++) {
		msg = message("device-change", "dri/card0");
		memset((char *)&msg + i * NDEVD_MSG, 'x', NDEVD_MSG);
		CHECK(parse(&msg, sizeof(msg), path, sizeof(path)) == UD_ACTION_NONE,
		    "unterminated field accepted");
	}
	msg = message("device-change", "dri/card0");
	memset(path, 'x', sizeof(path));
	memcpy(before, path, sizeof(path));
	CHECK(parse(&msg, sizeof(msg), path, 0) == UD_ACTION_NONE &&
	    memcmp(path, before, sizeof(path)) == 0, "zero output capacity");
	CHECK(parse(&msg, sizeof(msg), path, 1) == UD_ACTION_NONE && path[0] == 0,
	    "short output capacity");
	CHECK(parse(&msg, sizeof(msg), path, strlen("/dev/dri/card0")) == UD_ACTION_NONE,
	    "truncated path accepted");
	CHECK(socketpair(AF_UNIX, TEST_PACKET_SOCKET, 0, sockets) == 0,
	    "socketpair unavailable");
	memset(packet, 'x', sizeof(packet));
	memcpy(packet, &msg, sizeof(msg));
	for (i = sizeof(msg) - 1; i <= sizeof(packet); i++) {
		CHECK(send(sockets[0], packet, i, 0) == (ssize_t)i, "send record");
		{
			ssize_t length;

			/* This declaration comes verbatim from the real monitor loop. */
#include "receive-buffer.inc"
			length = recv(sockets[1], event, sizeof(event), MSG_WAITALL);
			CHECK(length > 0, "receive record");
			action = parse(event, (size_t)length, path, sizeof(path));
		}
		CHECK(action == (i == sizeof(msg) ? UD_ACTION_HOTPLUG : UD_ACTION_NONE),
		    "socket record length lost");
	}
	CHECK(close(sockets[0]) == 0 && close(sockets[1]) == 0, "socket cleanup");
	byte = 0;
	CHECK(parse(&byte, 1, path, sizeof(path)) == UD_ACTION_NONE,
	    "short backing allocation read");
	printf("PASS native change, drm_minor filters, malformed packets; record socket type=%d\n", TEST_PACKET_SOCKET);
	return (0);
}
