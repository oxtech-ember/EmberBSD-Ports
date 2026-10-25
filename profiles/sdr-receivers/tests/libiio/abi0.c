/* SPDX-License-Identifier: BSD-2-Clause */
#include <iio.h>
#include <errno.h>
#include <stdint.h>
#include <pthread.h>
#include <time.h>
#include <stdio.h>
#include <string.h>
#define CHECK(x) do { if (!(x)) { fprintf(stderr,"FAIL %d: %s\n", __LINE__, #x); return 1; } } while (0)
static void *cancel_read(void *buffer)
{
    const struct timespec delay = {0, 50000000};
    nanosleep(&delay, NULL);
    iio_buffer_cancel(buffer);
    return NULL;
}
int main(int argc, char **argv)
{
    struct iio_context *ctx;
    struct iio_device *dev, *phy;
    struct iio_channel *i, *q, *lo;
    struct iio_buffer *buf;
    long long freq;
    char text[32];
    ssize_t count;
    pthread_t canceller;
    unsigned major, minor;
    char tag[8];
    CHECK(argc == 3);
    iio_library_get_version(&major, &minor, tag);
    CHECK(major == 1 && minor == 0);
    CHECK(iio_has_backend("usb"));
    CHECK(iio_create_context_from_uri("invalid:fixture") == NULL);
    ctx = iio_create_context_from_uri(argv[1]); CHECK(ctx != NULL);
    CHECK(iio_context_set_timeout(ctx, 500) == 0);
    dev = iio_context_find_device(ctx, "cf-ad9361-lpc");
    phy = iio_context_find_device(ctx, "ad9361-phy"); CHECK(dev && phy);
    lo = iio_device_find_channel(phy, "altvoltage0", true); CHECK(lo);
    CHECK(iio_channel_attr_write_longlong(lo, "frequency", 1090000000) == 0);
    CHECK(iio_channel_attr_read_longlong(lo, "frequency", &freq) == 0 && freq == 1090000000);
    CHECK(iio_channel_attr_read(lo, "missing", text, sizeof(text)) == -ENOENT);
    i = iio_device_find_channel(dev, "voltage0", false);
    q = iio_device_find_channel(dev, "voltage1", false); CHECK(i && q);
    iio_channel_enable(i); iio_channel_enable(q);
    CHECK(iio_device_set_kernel_buffers_count(dev, 1) == 0);
    buf = iio_device_create_buffer(dev, 4, false); CHECK(buf);
    CHECK(iio_buffer_step(buf) == 4);
    if (!strcmp(argv[2], "cancel")) CHECK(pthread_create(&canceller, NULL, cancel_read, buf) == 0);
    count = iio_buffer_refill(buf);
    if (!strcmp(argv[2], "cancel")) {
        CHECK(pthread_join(canceller, NULL) == 0);
        CHECK(count == -EBADF);
    }
    if (!strcmp(argv[2], "full")) {
        const int16_t expected[8] = { -3, 101, -2, 102, -1, 103, 0, 104 };
        CHECK(count == 16);
        CHECK((char *)iio_buffer_end(buf) - (char *)iio_buffer_first(buf, i) == 16);
        CHECK(memcmp(iio_buffer_first(buf, i), expected, sizeof(expected)) == 0);
    } else {
        /* A partial legacy read must not expose uninitialized trailing IQ. */
        CHECK(count < 0);
    }
    iio_buffer_destroy(buf);
    iio_context_destroy(ctx);
    printf("PASS ABI0 %s: explicit context, attributes, buffer and close\n", argv[2]);
    return 0;
}
