/* SPDX-License-Identifier: BSD-2-Clause */
/* Origin: EmberBSD (AI-assisted). Records NetBSD netbt HCI socket traffic
 * to a BTSnoop file that Wireshark reads as "Bluetooth HCI H4", without
 * Linux BlueZ dependencies.
 */
#include <sys/types.h>
#include <sys/socket.h>
#include <sys/time.h>
#include <sys/endian.h>

#include <netbt/bluetooth.h>
#include <netbt/hci.h>

#include <errno.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#define BTSNOOP_MAGIC		"btsnoop"
#define BTSNOOP_VERSION		1
#define BTSNOOP_DATALINK_HCI_H4	1002
/* BTSnoop counts microseconds since 0000-01-01T00:00:00 UTC. */
#define BTSNOOP_EPOCH_OFFSET_US	0x00dcddb30f2f8000ULL

#define MAX_HCI_PACKET		(1 + 4 + 65535)

static volatile sig_atomic_t stop_requested;

static void
on_signal(int signo)
{

	stop_requested = 1;
}

static void
put_be32(uint8_t *buf, uint32_t value)
{

	buf[0] = (uint8_t)(value >> 24);
	buf[1] = (uint8_t)(value >> 16);
	buf[2] = (uint8_t)(value >> 8);
	buf[3] = (uint8_t)value;
}

static void
put_be64(uint8_t *buf, uint64_t value)
{
	int i;

	for (i = 0; i < 8; i++)
		buf[i] = (uint8_t)(value >> (56 - 8 * i));
}

static int
write_record(FILE *out, const uint8_t *data, size_t len, int received,
    uint32_t drops, const struct timeval *tv)
{
	uint8_t header[24];
	uint64_t usecs;

	if (len > UINT32_MAX)
		return -1;

	put_be32(&header[0], (uint32_t)len);		/* original length */
	put_be32(&header[4], (uint32_t)len);		/* included length */
	/* Flag bit 0: 0 = host to controller, 1 = controller to host. */
	put_be32(&header[8], received ? 1u : 0u);
	put_be32(&header[12], drops);
	usecs = (uint64_t)tv->tv_sec * 1000000 + (uint64_t)tv->tv_usec;
	put_be64(&header[16], usecs + BTSNOOP_EPOCH_OFFSET_US);

	if (fwrite(header, sizeof(header), 1, out) != 1)
		return -1;
	if (len > 0 && fwrite(data, len, 1, out) != 1)
		return -1;
	return 0;
}

static const char *
packet_type_name(uint8_t type)
{

	switch (type) {
	case HCI_CMD_PKT:		return "command";
	case HCI_ACL_DATA_PKT:		return "acl-data";
	case HCI_SCO_DATA_PKT:		return "sco-data";
	case HCI_EVENT_PKT:		return "event";
	default:			return "unknown";
	}
}

static void
usage(void)
{

	fprintf(stderr, "usage: hcisnoop [-o file] [-q]\n");
}

int
main(int argc, char *argv[])
{
	const char *output = "-";
	struct sockaddr_bt bind_addr;
	struct hci_filter all_packets;
	struct msghdr msg;
	struct iovec iov;
	struct cmsghdr *cmsg;
	struct timeval fallback, stamp;
	struct sigaction sigact;
	uint8_t packet[MAX_HCI_PACKET];
	uint8_t control[CMSG_SPACE(sizeof(int)) + CMSG_SPACE(sizeof(struct timeval))];
	uint32_t drops = 0;
	uint64_t counts[5] = {0, 0, 0, 0, 0};
	uint64_t total = 0;
	uint8_t file_header[16];
	FILE *out;
	ssize_t len;
	int ch, quiet = 0, s, received;
	int stdout_output = 1;

	while ((ch = getopt(argc, argv, "o:q")) != -1) {
		switch (ch) {
		case 'o':
			output = optarg;
			break;
		case 'q':
			quiet = 1;
			break;
		default:
			usage();
			return 2;
		}
	}
	argc -= optind;
	argv += optind;
	if (argc > 0) {
		usage();
		return 2;
	}

	if (strcmp(output, "-") == 0) {
		out = stdout;
	} else {
		out = fopen(output, "wb");
		stdout_output = 0;
	}
	if (out == NULL) {
		fprintf(stderr, "hcisnoop: fopen %s: %s\n", output,
		    strerror(errno));
		return 1;
	}

	memset(&sigact, 0, sizeof(sigact));
	sigact.sa_handler = on_signal;
	if (sigaction(SIGINT, &sigact, NULL) != 0 ||
	    sigaction(SIGTERM, &sigact, NULL) != 0) {
		fprintf(stderr, "hcisnoop: sigaction: %s\n", strerror(errno));
		return 1;
	}

	/*
	 * A raw HCI socket bound to the any address listens to every unit
	 * (promiscuous, see hci_bind(9) in netbt). Packet, event and
	 * direction filters must be opened explicitly; the default tap
	 * only carries command-complete and command-status events.
	 */
	s = socket(PF_BLUETOOTH, SOCK_RAW, BTPROTO_HCI);
	if (s < 0) {
		fprintf(stderr, "hcisnoop: socket: %s\n", strerror(errno));
		return 1;
	}
	memset(&bind_addr, 0, sizeof(bind_addr));
	bind_addr.bt_len = sizeof(bind_addr);
	bind_addr.bt_family = AF_BLUETOOTH;
	bdaddr_copy(&bind_addr.bt_bdaddr, BDADDR_ANY);
	if (bind(s, (struct sockaddr *)&bind_addr, sizeof(bind_addr)) < 0) {
		fprintf(stderr, "hcisnoop: bind: %s\n", strerror(errno));
		return 1;
	}
	memset(&all_packets, 0xff, sizeof(all_packets));
	if (setsockopt(s, BTPROTO_HCI, SO_HCI_PKT_FILTER, &all_packets,
	    sizeof(all_packets)) < 0 ||
	    setsockopt(s, BTPROTO_HCI, SO_HCI_EVT_FILTER, &all_packets,
	    sizeof(all_packets)) < 0) {
		fprintf(stderr, "hcisnoop: setsockopt filter: %s\n",
		    strerror(errno));
		return 1;
	}
	ch = 1;
	if (setsockopt(s, BTPROTO_HCI, SO_HCI_DIRECTION, &ch, sizeof(ch)) < 0) {
		fprintf(stderr, "hcisnoop: setsockopt direction: %s\n",
		    strerror(errno));
		return 1;
	}
	if (setsockopt(s, SOL_SOCKET, SO_TIMESTAMP, &ch, sizeof(ch)) < 0) {
		fprintf(stderr, "hcisnoop: setsockopt timestamp: %s\n",
		    strerror(errno));
		return 1;
	}

	memcpy(file_header, BTSNOOP_MAGIC, 8);
	put_be32(&file_header[8], BTSNOOP_VERSION);
	put_be32(&file_header[12], BTSNOOP_DATALINK_HCI_H4);
	if (fwrite(file_header, sizeof(file_header), 1, out) != 1) {
		fprintf(stderr, "hcisnoop: write header: %s\n",
		    strerror(errno));
		return 1;
	}

	while (!stop_requested) {
		memset(&msg, 0, sizeof(msg));
		iov.iov_base = packet;
		iov.iov_len = sizeof(packet);
		msg.msg_iov = &iov;
		msg.msg_iovlen = 1;
		msg.msg_control = control;
		msg.msg_controllen = sizeof(control);
		len = recvmsg(s, &msg, 0);
		if (len < 0) {
			if (errno == EINTR)
				break;
			if (errno == ENOBUFS) {
				drops++;
				continue;
			}
			fprintf(stderr, "hcisnoop: recvmsg: %s\n",
			    strerror(errno));
			return 1;
		}
		if (len == 0)
			continue;

		received = -1;
		gettimeofday(&fallback, NULL);
		stamp = fallback;
		for (cmsg = CMSG_FIRSTHDR(&msg); cmsg != NULL;
		    cmsg = CMSG_NXTHDR(&msg, cmsg)) {
			if (cmsg->cmsg_level == BTPROTO_HCI &&
			    cmsg->cmsg_type == SCM_HCI_DIRECTION &&
			    cmsg->cmsg_len == CMSG_LEN(sizeof(int))) {
				received = *(int *)CMSG_DATA(cmsg);
			} else if (cmsg->cmsg_level == SOL_SOCKET &&
			    cmsg->cmsg_type == SCM_TIMESTAMP &&
			    cmsg->cmsg_len == CMSG_LEN(sizeof(struct timeval))) {
				memcpy(&stamp, CMSG_DATA(cmsg),
				    sizeof(stamp));
			}
		}
		if (received < 0) {
			/*
			 * Without the direction control message the
			 * direction is unknown; record as sent. The
			 * socket option above should prevent this.
			 */
			received = 0;
		}

		if (write_record(out, packet, (size_t)len, received, drops,
		    &stamp) != 0) {
			fprintf(stderr, "hcisnoop: write record: %s\n",
			    strerror(errno));
			return 1;
		}
		if (packet[0] < sizeof(counts) / sizeof(counts[0]))
			counts[packet[0]]++;
		total++;
		if (!quiet && total % 100 == 0)
			fflush(out);
	}

	if (fflush(out) != 0 || (stdout_output == 0 && fsync(fileno(out)) != 0
	    && errno != EINVAL)) {
		fprintf(stderr, "hcisnoop: flush: %s\n", strerror(errno));
		return 1;
	}
	fclose(out);
	if (!quiet)
		fprintf(stderr, "hcisnoop: %llu packets",
		    (unsigned long long)total);
	if (!quiet && drops > 0)
		fprintf(stderr, ", %u dropped", drops);
	if (!quiet) {
		fprintf(stderr, " (%llu commands, %llu acl, %llu sco, "
		    "%llu events)\n",
		    (unsigned long long)counts[HCI_CMD_PKT],
		    (unsigned long long)counts[HCI_ACL_DATA_PKT],
		    (unsigned long long)counts[HCI_SCO_DATA_PKT],
		    (unsigned long long)counts[HCI_EVENT_PKT]);
	}
	return 0;
}
