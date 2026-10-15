/* SPDX-License-Identifier: MIT
 * Copyright (c) 2026 EmberBSD contributors (AI-assisted).
 * Include the actual FFmpeg RTP TU; upstream code retains its own license.
 */
#include RTP_UNIT_SOURCE
#include <stdio.h>

void unit_rtp_info(RTPDemuxContext *, const char *);
void unit_range_npt(const char *, int64_t *, int64_t *);
static unsigned int failures, checks;

static void
check_value(const char *name, int64_t actual, int64_t expected)
{
	checks++;
	if (actual != expected)
		failures++;
	printf("{\"case\":\"%s\",\"actual\":%" PRId64 ",\"expected\":%"
	    PRId64 ",\"ok\":%s}\n", name, actual, expected,
	    actual == expected ? "true" : "false");
}

static void
init_clock(RTPDemuxContext *s, AVFormatContext *format)
{
	memset(s, 0, sizeof(*s));
	s->ic = format;
	s->st = format->streams[0];
	s->last_sr.ntp_timestamp = AV_NOPTS_VALUE;
	s->first_rtcp_ntp_time = AV_NOPTS_VALUE;
}

static int64_t
packet_pts(RTPDemuxContext *s, AVPacket *packet, uint32_t timestamp)
{
	av_packet_unref(packet);
	finalize_packet(s, packet, timestamp);
	return packet->pts;
}

static void
sender_report(RTPDemuxContext *s, uint32_t timestamp)
{
	uint8_t report[28] = {0x80, 200, 0, 6};

	AV_WB32(report + 4, 0x13572468);
	AV_WB64(report + 8, UINT64_C(3900000000) << 32);
	AV_WB32(report + 16, timestamp);
	/* A valid RTCP SR updates state but emits no media packet. */
	check_value("RTCP valid packet",
	    rtcp_parse_packet(s, report, sizeof(report)), -1);
}

int
main(void)
{
	AVFormatContext *format = avformat_alloc_context();
	AVPacket *packet = av_packet_alloc();
	RTPDemuxContext s;
	const uint32_t bases[] = {0, 123, 0x80000000U, 0xffffdcd8U};
	const char *names[] = {"zero clock", "nonzero control",
	    "high-bit control", "wrap across zero"};
	const char *invalid[] = {"", ";rtptime=", ";rtptime=-1",
	    ";rtptime=4294967296", ";rtptime=1x"};
	char line[200];
	unsigned int i, j;
	uint32_t timestamp;

	if (format == NULL || packet == NULL ||
	    avformat_new_stream(format, NULL) == NULL) {
		av_packet_free(&packet);
		avformat_free_context(format);
		return 2;
	}
	format->streams[0]->time_base = (AVRational){1, 90000};
	for (i = 0; i < 4; i++) {
		init_clock(&s, format);
		for (j = 0; j < 4; j++) {
			timestamp = bases[i] + j * 9000U;
			check_value(names[i], packet_pts(&s, packet, timestamp),
			    (int64_t)j * 9000);
		}
	}
	init_clock(&s, format);
	check_value("repeat zero 1", packet_pts(&s, packet, 0), 0);
	check_value("repeat zero 2", packet_pts(&s, packet, 0), 0);
	check_value("zero then tick", packet_pts(&s, packet, 9000), 9000);
	init_clock(&s, format);
	sender_report(&s, 0);
	check_value("RTCP zero pre-first", packet_pts(&s, packet, 9000), 9000);
	init_clock(&s, format);
	sender_report(&s, 0xffffff00U);
	check_value("RTCP pre-first wrap",
	    packet_pts(&s, packet, 0xffffff00U + 9000U), 9000);
	init_clock(&s, format);
	check_value("RTP zero before SR", packet_pts(&s, packet, 0), 0);
	sender_report(&s, 9000);
	check_value("SR retains zero base", s.base_timestamp, 0);
	check_value("RTP after SR", packet_pts(&s, packet, 18000), 18000);
	init_clock(&s, format);
	unit_rtp_info(&s, "url=rtsp://127.0.0.1/camera;seq=1;rtptime=0");
	check_value("RTP-Info zero origin", packet_pts(&s, packet, 9000), 9000);
	init_clock(&s, format);
	snprintf(line, sizeof(line), "url=rtsp://127.0.0.1/camera;rtptime=%"
	    PRIu32, 0xffffff00U);
	unit_rtp_info(&s, line);
	check_value("RTP-Info pre-first wrap",
	    packet_pts(&s, packet, 0xffffff00U + 9000U), 9000);
	init_clock(&s, format);
	unit_rtp_info(&s, "url=rtsp://127.0.0.1/camera;rtptime=4294967295");
	check_value("RTP-Info UINT32_MAX origin", packet_pts(&s, packet, 0), 1);
	for (i = 0; i < 5; i++) {
		init_clock(&s, format);
		s.base_timestamp = 17;
		snprintf(line, sizeof(line), "url=rtsp://127.0.0.1/camera;seq=1%s",
		    invalid[i]);
		unit_rtp_info(&s, line);
		check_value("RTP-Info absent/invalid", s.base_timestamp, 17);
	}
	init_clock(&s, format);
	s.base_timestamp = 17;
	unit_rtp_info(&s, "url=rtsp://127.0.0.1/other;rtptime=0,"
	    "url=rtsp://127.0.0.1/camera;seq=1");
	check_value("RTP-Info entry presence reset", s.base_timestamp, 17);
#ifdef CLOCK_PATCHED
	s.base_timestamp = 123;
	s.timestamp = 456;
	s.unwrapped_timestamp = 789;
	s.base_timestamp_initialized = s.timestamp_initialized = 1;
	s.rtcp_ts_offset = 999;
	ff_rtp_reset_timestamps(&s);
	check_value("reset origin", s.base_timestamp, 0);
	check_value("reset previous", s.timestamp, 0);
	check_value("reset origin flag", s.base_timestamp_initialized, 0);
	check_value("reset previous flag", s.timestamp_initialized, 0);
	check_value("reset unwrapped", s.unwrapped_timestamp, 0);
	check_value("reset SR offset", s.rtcp_ts_offset, 0);
	check_value("reset SR sentinel", s.last_sr.ntp_timestamp, AV_NOPTS_VALUE);
	unit_rtp_info(&s, "url=rtsp://127.0.0.1/camera;rtptime=0");
	check_value("zero after real reset", packet_pts(&s, packet, 9000), 9000);
#endif
	{
		static const char *ranges[] = {"", "clock=bad", "npt=1.25-2.5", "  npt=0-"};
		static const int64_t starts[] = {AV_NOPTS_VALUE, AV_NOPTS_VALUE, 1250000, 0};
		static const int64_t ends[] = {AV_NOPTS_VALUE, AV_NOPTS_VALUE, 2500000, AV_NOPTS_VALUE};
		unsigned int range_index;
		for (range_index = 0; range_index < 4; range_index++) {
			int64_t start = 111, end = 222;
			unit_range_npt(ranges[range_index], &start, &end);
			check_value("NPT range start", start, starts[range_index]);
			check_value("NPT range end", end, ends[range_index]);
		}
	}
	av_packet_free(&packet);
	avformat_free_context(format);
	printf("{\"checks\":%u,\"failures\":%u}\n", checks, failures);
	return failures != 0 ? 1 : 0;
}
