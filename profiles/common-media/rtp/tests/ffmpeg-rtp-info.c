/* SPDX-License-Identifier: MIT
 * Copyright (c) 2026 EmberBSD contributors (AI-assisted).
 * The included FFmpeg RTSP source retains its upstream license.
 */
#include RTP_INFO_SOURCE

void unit_rtp_info(RTPDemuxContext *, const char *);
void unit_range_npt(const char *, int64_t *, int64_t *);

void
unit_range_npt(const char *input, int64_t *start, int64_t *end)
{
	rtsp_parse_range_npt(input, start, end);
}

void
unit_rtp_info(RTPDemuxContext *context, const char *header)
{
	RTSPState state = {0};
	RTSPStream stream = {0};
	RTSPStream *streams[] = {&stream};

	state.transport = RTSP_TRANSPORT_RTP;
	state.nb_rtsp_streams = 1;
	state.rtsp_streams = streams;
	stream.transport_priv = context;
	av_strlcpy(stream.control_url, "rtsp://127.0.0.1/camera",
	    sizeof(stream.control_url));
	rtsp_parse_rtp_info(&state, header);
}
