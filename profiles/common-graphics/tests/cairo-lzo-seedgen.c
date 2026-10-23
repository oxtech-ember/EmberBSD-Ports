/* SPDX-License-Identifier: BSD-2-Clause */
/* Copyright (c) 2026 EmberBSD contributors. */
/* Origin: EmberBSD; AI-assisted diagnostic fuzz corpus generator. */

#include <lzo/lzo2a.h>
#include <lzo/lzoconf.h>
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>

#define EXPANDED_SIZE 32768
#define OUTPUT_SIZE (EXPANDED_SIZE + EXPANDED_SIZE / 16 + 128)

static int
write_seed(const char *directory, const char *name, unsigned int mode,
           unsigned int declared_size, unsigned int expanded_size)
{
    unsigned char source[EXPANDED_SIZE];
    unsigned char compressed[OUTPUT_SIZE];
    unsigned char *work;
    lzo_uint compressed_size = sizeof(compressed);
    char path[1024];
    FILE *output;
    int status;

    memset(source, 'A', expanded_size);
    work = malloc(LZO2A_999_MEM_COMPRESS);
    if (work == NULL)
        return 1;
    status = lzo2a_999_compress(source, expanded_size, compressed,
                                &compressed_size, work);
    free(work);
    if (status != LZO_E_OK)
        return 1;

    if (snprintf(path, sizeof(path), "%s/%s", directory, name) >=
        (int) sizeof(path))
        return 1;
    output = fopen(path, "wb");
    if (output == NULL)
        return 1;
    if (fputc((int) mode, output) == EOF) {
        fclose(output);
        return 1;
    }
    {
        unsigned char header[4];

        header[0] = (unsigned char) (declared_size >> 24);
        header[1] = (unsigned char) (declared_size >> 16);
        header[2] = (unsigned char) (declared_size >> 8);
        header[3] = (unsigned char) declared_size;
        if (fwrite(header, 1, sizeof(header), output) != sizeof(header) ||
            fwrite(compressed, 1, compressed_size, output) != compressed_size) {
            fclose(output);
            return 1;
        }
    }
    return fclose(output) != 0;
}

int
main(int argc, char **argv)
{
    static const struct {
        const char *valid;
        const char *oversized;
        unsigned int mode;
        unsigned int declared_size;
        unsigned int valid_size;
    } cases[] = {
        { "direct-valid", "direct-oversized", 0, 4, 4 },
        { "file-valid", "file-oversized", 1, 32, 32 },
        { "font-valid", "font-oversized", 2, 32, 32 }
    };

    if (argc != 2 || lzo_init() != LZO_E_OK)
        return 2;
    if (mkdir(argv[1], 0755) != 0 && errno != EEXIST)
        return 2;

    for (size_t i = 0; i < sizeof(cases) / sizeof(cases[0]); i++) {
        if (write_seed(argv[1], cases[i].valid, cases[i].mode,
                       cases[i].declared_size, cases[i].valid_size) != 0 ||
            write_seed(argv[1], cases[i].oversized, cases[i].mode,
                       cases[i].declared_size, EXPANDED_SIZE) != 0)
            return 1;
    }
    return 0;
}
