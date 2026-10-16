/* SPDX-License-Identifier: BSD-2-Clause */
/* Origin: EmberBSD (AI-assisted). Compile-time native/bundled ABI comparison. */
#include <sys/types.h>
#include <stddef.h>
#include <stdint.h>

#ifdef NATIVE_VIDEOIO
#include <sys/videoio.h>
#else
#include "ext/videodev2.h"
#endif

#define SIZE(type) sizeof(struct type)
#define OFFSET(type, member) offsetof(struct type, member)

const uint64_t ember_videoio_abi[] = {
	SIZE(v4l2_capability),
	SIZE(v4l2_format),
	SIZE(v4l2_buffer),
	SIZE(v4l2_plane),
	SIZE(v4l2_requestbuffers),
	SIZE(v4l2_ext_control),
	SIZE(v4l2_ext_controls),
	SIZE(v4l2_event),
	SIZE(v4l2_create_buffers),
	OFFSET(v4l2_buffer, timestamp),
	OFFSET(v4l2_buffer, m),
	OFFSET(v4l2_buffer, length),
	OFFSET(v4l2_ext_controls, controls),
	VIDIOC_CREATE_BUFS,
	VIDIOC_CROPCAP,
	VIDIOC_DECODER_CMD,
	VIDIOC_DQBUF,
	VIDIOC_DQEVENT,
	VIDIOC_ENCODER_CMD,
	VIDIOC_ENUMINPUT,
	VIDIOC_ENUMSTD,
	VIDIOC_ENUM_FMT,
	VIDIOC_ENUM_FRAMEINTERVALS,
	VIDIOC_ENUM_FRAMESIZES,
	VIDIOC_EXPBUF,
	VIDIOC_G_CROP,
	VIDIOC_G_CTRL,
	VIDIOC_G_FMT,
	VIDIOC_G_FREQUENCY,
	VIDIOC_G_INPUT,
	VIDIOC_G_OUTPUT,
	VIDIOC_G_PARM,
	VIDIOC_G_SELECTION,
	VIDIOC_G_STD,
	VIDIOC_G_TUNER,
	VIDIOC_QBUF,
	VIDIOC_QUERYBUF,
	VIDIOC_QUERYCAP,
	VIDIOC_QUERYCTRL,
	VIDIOC_QUERYMENU,
	VIDIOC_QUERY_DV_TIMINGS,
	VIDIOC_REQBUFS,
	VIDIOC_STREAMOFF,
	VIDIOC_STREAMON,
	VIDIOC_SUBSCRIBE_EVENT,
	VIDIOC_S_CROP,
	VIDIOC_S_CTRL,
	VIDIOC_S_DV_TIMINGS,
	VIDIOC_S_EXT_CTRLS,
	VIDIOC_S_FMT,
	VIDIOC_S_FREQUENCY,
	VIDIOC_S_INPUT,
	VIDIOC_S_OUTPUT,
	VIDIOC_S_PARM,
	VIDIOC_S_SELECTION,
	VIDIOC_S_STD,
	VIDIOC_TRY_FMT,
	VIDIOC_G_EXT_CTRLS
};
