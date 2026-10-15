/* SPDX-License-Identifier: MIT
 * Copyright (c) 2026 EmberBSD contributors (AI-assisted).
 * Feed independently captured real RTP NALs to the actual FFmpeg parser.
 * Records are BE32 length, BE64 observed RTP timestamp, then AnnexB bytes.
 */
#include <inttypes.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <libavcodec/avcodec.h>
#include <libavutil/intreadwrite.h>
#include <libavutil/mem.h>

int unit_av_parser_parse2(AVCodecParserContext *, AVCodecContext *, uint8_t **,
    int *, const uint8_t *, int, int64_t, int64_t, int64_t);

struct observation {
	int ok;
	unsigned int frames;
	int64_t pts[100], positions[100];
};

static void
observe(struct observation *s, const AVCodecParserContext *parser, int64_t pos)
{
	if (s->frames >= 100) {
		s->ok = 0;
		return;
	}
	s->pts[s->frames] = parser->pts;
	s->positions[s->frames] = parser->pos;
	if (parser->pts != (int64_t)s->frames * 9000 || parser->pos != pos)
		s->ok = 0;
	s->frames++;
}

int
main(int argc, char **argv)
{
	struct observation s = {1, 0, {0}, {0}};
	AVCodecContext *decoder = NULL;
	AVCodecParserContext *parser = NULL;
	FILE *input = NULL;
	uint8_t header[12], *buffer = NULL, *output, *cursor;
	int output_size, consumed, remaining;
	unsigned int records = 0, i;
	int64_t position, pts;
	uint64_t timestamp;
	uint32_t length;
	size_t got, total = 0;

	if (argc != 3 || (strcmp(argv[2], "-1") != 0 &&
	    strcmp(argv[2], "0") != 0))
		return 2;
	position = strcmp(argv[2], "-1") == 0 ? -1 : 0;
	input = fopen(argv[1], "rb");
	decoder = avcodec_alloc_context3(avcodec_find_decoder(AV_CODEC_ID_HEVC));
	parser = av_parser_init(AV_CODEC_ID_HEVC);
	if (input == NULL || decoder == NULL || parser == NULL) {
		s.ok = 0;
		goto done;
	}
	decoder->codec_id = AV_CODEC_ID_HEVC;
	while ((got = fread(header, 1, sizeof(header), input)) != 0) {
		if (got != sizeof(header) || ++records > 4096) {
			s.ok = 0;
			break;
		}
		length = AV_RB32(header);
		timestamp = AV_RB64(header + 4);
		if (length == 0 || length > 1000000 ||
		    length > 16777216 - total || timestamp > 351000 ||
		    timestamp % 9000 != 0) {
			s.ok = 0;
			break;
		}
		total += length;
		pts = (int64_t)timestamp;
		buffer = av_mallocz((size_t)length + AV_INPUT_BUFFER_PADDING_SIZE);
		if (buffer == NULL || fread(buffer, 1, length, input) != length) {
			s.ok = 0;
			break;
		}
		cursor = buffer;
		remaining = (int)length;
		while (remaining != 0) {
			consumed = unit_av_parser_parse2(parser, decoder, &output,
			    &output_size, cursor, remaining, pts, pts, position);
			if (consumed < 0 || consumed > remaining ||
			    (consumed == 0 && output_size == 0)) {
				s.ok = 0;
				break;
			}
			if (output_size != 0)
				observe(&s, parser, position);
			cursor += consumed;
			remaining -= consumed;
			pts = AV_NOPTS_VALUE;
		}
		av_freep(&buffer);
	}
	if (ferror(input))
		s.ok = 0;
	unit_av_parser_parse2(parser, decoder, &output, &output_size, NULL, 0,
	    AV_NOPTS_VALUE, AV_NOPTS_VALUE, position);
	if (output_size != 0)
		observe(&s, parser, position);
	if (s.frames != 40)
		s.ok = 0;
done:
	printf("{\"ok\":%s,\"position\":%" PRId64 ",\"frames\":%u,\"pts\":[",
	    s.ok ? "true" : "false", position, s.frames);
	for (i = 0; i < s.frames; i++)
		printf("%s%" PRId64, i != 0 ? "," : "", s.pts[i]);
	printf("],\"output_positions\":[");
	for (i = 0; i < s.frames; i++)
		printf("%s%" PRId64, i != 0 ? "," : "", s.positions[i]);
	puts("]}");
	av_freep(&buffer);
	if (input != NULL && fclose(input) != 0)
		s.ok = 0;
	if (parser != NULL)
		av_parser_close(parser);
	avcodec_free_context(&decoder);
	return s.ok ? 0 : 1;
}
