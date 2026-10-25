#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD; independently generated ITU-R M.1371 test signals.
"""Write synthetic CF32 AIS A/B signals. No recordings, devices or network.

Message 1 fields follow ITU-R M.1371. HDLC uses reflected CRC-16/X-25,
LSB-first octets, zero insertion and NRZI. Gaussian filtering uses BT=0.4.
These idealized fixtures test the decoder. They do not establish RF reception.
"""
import math
from pathlib import Path
import struct
import sys

RATE = 96000
SPS = RATE // 9600


def crc_x25(data):
    value = 0xffff
    for byte in data:
        value ^= byte
        for _ in range(8):
            value = (value >> 1) ^ (0x8408 if value & 1 else 0)
    return value ^ 0xffff


def payload(mmsi, unavailable):
    # Type, repeat, MMSI, nav, ROT unavailable, SOG, accuracy, lon, lat,
    # COG, heading unavailable, second, maneuver, spare, RAIM, radio.
    fields = [(1, 6), (0, 2), (mmsi, 30), (0, 4), (128, 8), (100, 10),
              (0, 1), ((181 * 600000) if unavailable else 0, 28),
              ((91 * 600000) if unavailable else 0, 27), (900, 12),
              (511, 9), (30, 6), (0, 2), (0, 3), (0, 1), (0, 19)]
    bits = ''.join(format(value, '0%db' % width) for value, width in fields)
    assert len(bits) == 168
    return int(bits, 2).to_bytes(21, 'big')


def burst(data, bad_fcs):
    crc = crc_x25(data) ^ int(bad_fcs)
    wire = data + crc.to_bytes(2, 'little')
    stuffed = []
    ones = 0
    for byte in wire:
        for bit in range(8):
            value = (byte >> bit) & 1
            stuffed.append(value)
            ones = ones + 1 if value else 0
            if ones == 5:
                stuffed.append(0)
                ones = 0
    flag = [0, 1, 1, 1, 1, 1, 1, 0]
    bits = [0, 1] * 12 + flag + stuffed + flag + [0] * 24
    level = 1
    levels = []
    for bit in bits:
        if not bit:
            level = -level
        levels.extend([level] * SPS)
    kernel = [math.exp(-2 * (math.pi * 0.4 * (i / SPS)) ** 2 / math.log(2))
              for i in range(-2 * SPS, 2 * SPS + 1)]
    norm = sum(kernel)
    kernel = [value / norm for value in kernel]
    phase = 0.0
    samples = []
    for i in range(len(levels)):
        filtered = sum(weight * levels[j] for k, weight in enumerate(kernel)
                       if 0 <= (j := i + k - 2 * SPS) < len(levels))
        phase += math.pi * filtered / (2 * SPS)
        samples.append(complex(math.cos(phase), math.sin(phase)))
    return samples


def write_signal(path, bad_fcs):
    signal = [0j] * (2 * RATE)
    for channel, mmsi, unavailable in [(-25000, 123456789, False),
                                       (25000, 987654321, True)]:
        samples = burst(payload(mmsi, unavailable), bad_fcs)
        for repeat in range(4):
            start = int((0.25 + repeat * 0.4 + (0.1 if channel > 0 else 0)) * RATE)
            for index, sample in enumerate(samples):
                time = start + index
                carrier = complex(math.cos(2 * math.pi * channel * time / RATE),
                                  math.sin(2 * math.pi * channel * time / RATE))
                signal[time] += sample * carrier * 0.5
    with path.open('xb') as output:
        for sample in signal:
            output.write(struct.pack('<ff', sample.real, sample.imag))


if __name__ == '__main__':
    assert crc_x25(b'123456789') == 0x906e, 'CRC-16/X-25 check vector'
    directory = Path(sys.argv[1])
    directory.mkdir()
    write_signal(directory / 'valid.cf32', False)
    write_signal(directory / 'bad-fcs.cf32', True)
    print('Synthetic CF32: 96000 samples/s; A=123456789 at 0/0, B=987654321 unavailable; bad FCS differs only in CRC.')
