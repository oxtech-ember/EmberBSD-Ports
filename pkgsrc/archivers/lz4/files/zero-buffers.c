/* SPDX-License-Identifier: MIT */
/* Origin: EmberBSD (AI-assisted). Check zero-length LZ4 frame operations. */
#include <lz4frame.h>

#include <stdint.h>
#include <stdio.h>
#include <string.h>

static int
query(LZ4F_dctx *context, const LZ4F_frameInfo_t *expected)
{
	LZ4F_frameInfo_t info;
	size_t consumed = 0, result;

	memset(&info, 0, sizeof(info));
	result = LZ4F_getFrameInfo(context, &info, NULL, &consumed);
	return LZ4F_isError(result) || consumed != 0 ||
	    info.blockSizeID != expected->blockSizeID ||
	    info.blockMode != expected->blockMode;
}

static int
check(int random_input, LZ4F_blockMode_t mode)
{
	unsigned char input[140000], frame[150000], output[140000];
	LZ4F_preferences_t preferences;
	LZ4F_frameInfo_t info;
	LZ4F_dctx *context = NULL;
	uint32_t state = UINT32_C(0x8b5ad4ce);
	size_t frame_size, in_size, out_size, in_offset, out_offset, result, i;
	int status = 1;

	memset(&preferences, 0, sizeof(preferences));
	preferences.frameInfo.blockMode = mode;
	for (i = 0; i < sizeof(input); i++) {
		state ^= state << 13;
		state ^= state >> 17;
		state ^= state << 5;
		input[i] = random_input ? (unsigned char)state :
		    (unsigned char)(i % 17);
	}
	frame_size = LZ4F_compressFrame(frame, sizeof(frame), input,
	    sizeof(input), &preferences);
	if (LZ4F_isError(frame_size))
		return 1;
	result = LZ4F_createDecompressionContext(&context, LZ4F_VERSION);
	if (LZ4F_isError(result))
		return 2;

	/* A newly created decoder must allow a zero-length input/output call. */
	in_size = out_size = 0;
	result = LZ4F_decompress(context, NULL, &out_size, NULL, &in_size, NULL);
	if (LZ4F_isError(result) || in_size != 0 || out_size != 0)
		goto done;
	memset(&info, 0, sizeof(info));
	in_size = frame_size;
	result = LZ4F_getFrameInfo(context, &info, frame, &in_size);
	if (LZ4F_isError(result) || in_size == 0)
		goto done;
	in_offset = in_size;
	out_offset = 0;
	if (query(context, &info) || query(context, &info))
		goto done;

	/* Exercise both a buffered compressed block and a direct raw block. */
	in_size = frame_size - in_offset;
	out_size = 0;
	result = LZ4F_decompress(context, NULL, &out_size,
	    frame + in_offset, &in_size, NULL);
	if (LZ4F_isError(result) || out_size != 0)
		goto done;
	in_offset += in_size;
	if (query(context, &info))
		goto done;

	/* Empty input can flush one byte of a pending compressed block. */
	in_size = 0;
	out_size = 1;
	result = LZ4F_decompress(context, output, &out_size, NULL, &in_size, NULL);
	if (LZ4F_isError(result) || in_size != 0 || out_size > 1)
		goto done;
	out_offset += out_size;
	if (query(context, &info))
		goto done;

	for (i = 0; i < 16; i++) {
		in_size = frame_size - in_offset;
		out_size = sizeof(output) - out_offset;
		result = LZ4F_decompress(context, output + out_offset, &out_size,
		    frame + in_offset, &in_size, NULL);
		if (LZ4F_isError(result))
			goto done;
		in_offset += in_size;
		out_offset += out_size;
		if (result == 0)
			break;
		if (in_size == 0 && out_size == 0)
			goto done;
	}
	if (result != 0 || in_offset != frame_size ||
	    out_offset != sizeof(input) || memcmp(input, output, sizeof(input)))
		goto done;
	status = 0;
done:
	LZ4F_freeDecompressionContext(context);
	return status;
}

int
main(void)
{
	if (check(0, LZ4F_blockLinked) || check(1, LZ4F_blockLinked) ||
	    check(0, LZ4F_blockIndependent) || check(1, LZ4F_blockIndependent))
		return 1;
	puts("PASS LZ4 zero buffers, repeated queries and four full round trips");
	return 0;
}
