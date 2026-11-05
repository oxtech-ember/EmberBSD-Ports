/* SPDX-License-Identifier: BSD-2-Clause */
/* Origin: EmberBSD contributors (AI-assisted). */
/* Exercise the actual libavutil HDR serializer and case-insensitive replace. */
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include <libavutil/avstring.h>
#include <libavutil/hdr_dynamic_metadata.h>
#include <libavutil/mem.h>

static void
check_hdr(int tone)
{
    AVDynamicHDRPlus input = {0}, output = {0};
    size_t size = 0;
    input.num_windows = 1;
    input.targeted_system_display_maximum_luminance = (AVRational){1000, 1};
    for (int i = 0; i < 3; i++) input.params[0].maxscl[i] = (AVRational){0, 1};
    input.params[0].average_maxrgb = (AVRational){0, 1};
    input.params[0].fraction_bright_pixels = (AVRational){0, 1};
    input.params[0].tone_mapping_flag = tone;
    input.params[0].knee_point_x = (AVRational){1, 2};
    input.params[0].knee_point_y = (AVRational){1, 2};
    input.params[0].color_saturation_mapping_flag = 1;
    input.params[0].color_saturation_weight = (AVRational){13, 8};
    assert(av_dynamic_hdr_plus_to_t35(&input, NULL, &size) == 0 && size);
    uint8_t *data = av_malloc(size);
    assert(data);
    memset(data, 0xff, size);
    assert(av_dynamic_hdr_plus_to_t35(&input, &data, &size) == 0);
    assert(av_dynamic_hdr_plus_from_t35(&output, data, size) == 0);
    assert(output.params[0].tone_mapping_flag == tone);
    assert(output.params[0].color_saturation_mapping_flag == 1);
    assert(output.params[0].color_saturation_weight.num == 13);
    assert(output.params[0].color_saturation_weight.den == 8);
    av_free(data);
}

int
main(int argc, char **argv)
{
    assert(argc == 2);
    if (!strcmp(argv[1], "hdr")) {
        check_hdr(0);
        check_hdr(1);
    } else {
        assert(!strcmp(argv[1], "replace"));
        char *text = av_strireplace("Abc", "", "ignored");
        assert(text && !strcmp(text, "Abc"));
        av_free(text);
        text = av_strireplace("AbcAB", "ab", "x");
        assert(text && !strcmp(text, "xcx"));
        av_free(text);
    }
    puts("PASS: selected libavutil regression");
    return 0;
}
