/* SPDX-License-Identifier: BSD-2-Clause */
/* Copyright (c) 2026 EmberBSD contributors. */
/* Origin: EmberBSD; AI-assisted diagnostic fuzz harness. */

#include <cairo-script-interpreter.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>

#define MAX_SCRIPT_SIZE (65536 + 128)
#define LZO_TOKEN 154

enum fuzz_mode {
    FUZZ_IMAGE_DIRECT = 0,
    FUZZ_IMAGE_FILE = 1,
    FUZZ_FONT_SOURCE = 2
};

static uint32_t
read_be32(const uint8_t *p)
{
    return ((uint32_t) p[0] << 24) | ((uint32_t) p[1] << 16) |
           ((uint32_t) p[2] << 8) | (uint32_t) p[3];
}

static void
write_be32(uint8_t *p, uint32_t value)
{
    p[0] = (uint8_t) (value >> 24);
    p[1] = (uint8_t) (value >> 16);
    p[2] = (uint8_t) (value >> 8);
    p[3] = (uint8_t) value;
}

int
LLVMFuzzerTestOneInput(const uint8_t *data, size_t size)
{
    static const char *const prefixes[] = {
        "<< /width 1 /height 1 /source ",
        "<< /width 1 /height 1 /format 2 /source ",
        "<< /type 42 /source "
    };
    static const char suffix[] = " >> image pop\n";
    static const char font_suffix[] = " >> font pop\n";
    cairo_script_interpreter_t *interpreter;
    uint8_t *script;
    size_t compressed_size;
    size_t prefix_size;
    size_t suffix_size;
    size_t script_size;
    unsigned int mode;
    uint32_t declared_size;

    if (size < 6 || size > 65536)
        return 0;

    mode = data[0] % 3;
    declared_size = (read_be32(data + 1) % 65536) + 1;

    compressed_size = size - 5;
    prefix_size = 0;
    while (prefixes[mode][prefix_size] != '\0')
        prefix_size++;
    suffix_size = 0;
    while ((mode == FUZZ_FONT_SOURCE ? font_suffix : suffix)[suffix_size] != '\0')
        suffix_size++;
    script_size = prefix_size + 9 + compressed_size + suffix_size;
    if (script_size > MAX_SCRIPT_SIZE)
        return 0;

    script = malloc(script_size);
    if (script == NULL)
        return 0;

    {
        size_t offset = 0;

        for (size_t i = 0; i < prefix_size; i++)
            script[offset++] = (uint8_t) prefixes[mode][i];
        script[offset++] = LZO_TOKEN;
        write_be32(script + offset, (uint32_t) compressed_size);
        offset += 4;
        write_be32(script + offset, declared_size);
        offset += 4;
        for (size_t i = 0; i < compressed_size; i++)
            script[offset++] = data[i + 5];
        for (size_t i = 0; i < suffix_size; i++)
            script[offset++] = (uint8_t) (mode == FUZZ_FONT_SOURCE ?
                                          font_suffix[i] : suffix[i]);
    }

    interpreter = cairo_script_interpreter_create();
    if (interpreter != NULL) {
        cairo_status_t status;

        status = cairo_script_interpreter_feed_string(interpreter,
                                                       (const char *) script,
                                                       (int) script_size);
        if (status == CAIRO_STATUS_SUCCESS)
            (void) cairo_script_interpreter_finish(interpreter);
        (void) cairo_script_interpreter_destroy(interpreter);
    }

    free(script);
    return 0;
}

#ifdef CAIRO_LZO_FUZZ_REPLAY
int
main(int argc, char **argv)
{
    FILE *input;
    long file_size;
    uint8_t *data;
    size_t size;

    if (argc != 2)
        return 2;
    input = fopen(argv[1], "rb");
    if (input == NULL)
        return 2;
    if (fseek(input, 0, SEEK_END) != 0 || (file_size = ftell(input)) < 0 ||
        file_size > 65536 || fseek(input, 0, SEEK_SET) != 0) {
        fclose(input);
        return 2;
    }
    size = (size_t) file_size;
    data = malloc(size == 0 ? 1 : size);
    if (data == NULL) {
        fclose(input);
        return 2;
    }
    if (fread(data, 1, size, input) != size) {
        free(data);
        fclose(input);
        return 2;
    }
    if (fclose(input) != 0) {
        free(data);
        return 2;
    }

    (void) LLVMFuzzerTestOneInput(data, size);
    free(data);
    return 0;
}
#endif
