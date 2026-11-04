#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Original EmberBSD globe icon. No upstream artwork is used.
import math
import struct
import zlib
from pathlib import Path

SIZE = 128
SAMPLES = 4


def chunk(kind, data):
    return struct.pack('>I', len(data)) + kind + data + struct.pack('>I', zlib.crc32(kind + data))


def pixel(x, y):
    x = (x + 0.5) * 64 / (SIZE * SAMPLES) - 32
    y = (y + 0.5) * 64 / (SIZE * SAMPLES) - 32
    r = math.hypot(x, y)
    if r > 27:
        return (0, 0, 0, 0)
    circle = abs(r - 21) <= 1.5
    ellipse = abs(math.hypot(x / 10, y / 21) - 1) <= .12 and abs(y) <= 22.5
    bars = (abs(y - 7) <= 1.5 or abs(y + 7) <= 1.5) and abs(x) <= 20
    return (245, 242, 233, 255) if circle or ellipse or bars else (35, 56, 74, 255)


def main():
    rows = []
    for y in range(SIZE):
        row = bytearray([0])
        for x in range(SIZE):
            samples = [pixel(x*SAMPLES+dx, y*SAMPLES+dy) for dy in range(SAMPLES) for dx in range(SAMPLES)]
            row.extend(sum(sample[i] for sample in samples) // len(samples) for i in range(4))
        rows.append(row)
    png = b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', SIZE, SIZE, 8, 6, 0, 0, 0))
    png += chunk(b'IDAT', zlib.compress(b''.join(rows), 9)) + chunk(b'IEND', b'')
    Path(__file__).with_name('ember-browser.png').write_bytes(png)


if __name__ == '__main__':
    main()
