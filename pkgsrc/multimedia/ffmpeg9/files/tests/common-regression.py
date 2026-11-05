#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
"""Explicit host regression for the shared FFmpeg encryption and MOV patches."""
import argparse
import json
from pathlib import Path
import resource
import subprocess
import tempfile

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--cc', required=True, type=Path, help='selected native compiler')
parser.add_argument('--ffprobe', required=True, type=Path, help='selected FFmpeg ffprobe')
parser.add_argument('--cflag', action='append', default=[], help='compiler include/target flag')
parser.add_argument('--ldflag', action='append', default=[], help='library/link flag')
parser.add_argument('--cdsc', required=True, type=Path)
parser.add_argument('--rndr', required=True, type=Path)
parser.add_argument('--fragment-init', required=True, type=Path)
parser.add_argument('--fragment-media', required=True, type=Path)
args = parser.parse_args()


def bounded_stack():
    _, hard = resource.getrlimit(resource.RLIMIT_STACK)
    limit = 256 * 1024
    if hard != resource.RLIM_INFINITY:
        limit = min(limit, hard)
    resource.setrlimit(resource.RLIMIT_STACK, (limit, hard))


def probe(path, entries):
    result = subprocess.run([str(args.ffprobe), '-v', 'error', '-show_entries', entries,
                             '-of', 'json', str(path)], check=True, capture_output=True, text=True)
    return json.loads(result.stdout)


with tempfile.TemporaryDirectory(prefix='ffmpeg-common-regression-') as temp:
    executable = Path(temp) / 'encryption-init-info'
    source = Path(__file__).with_name('encryption-init-info.c')
    subprocess.run([str(args.cc), *args.cflag, '-UNDEBUG', str(source), *args.ldflag, '-o', str(executable)], check=True)
    subprocess.run([str(executable)], preexec_fn=bounded_stack, check=True)
    for sample in (args.cdsc, args.rndr, args.fragment_init):
        result = probe(sample, 'stream_group=index,id,nb_streams,type:stream_group_stream=index,id,codec_name,codec_type,codec_tag_string,extradata_size')
        groups = result.get('stream_groups', [])
        assert any(group.get('nb_streams') == 2 and group.get('type') == 'Track Reference' and
                   any(stream.get('codec_type') == 'video' and stream.get('id') == group.get('id')
                       for stream in group.get('streams', [])) and
                   any(stream.get('codec_name') == 'itut_t35' and stream.get('codec_type') == 'data' and
                       stream.get('codec_tag_string') == 'it35' and stream.get('extradata_size') == 5
                       for stream in group.get('streams', [])) for group in groups), sample
    combined = Path(temp) / 'fragmented.mp4'
    with combined.open('wb') as output:
        for sample in (args.fragment_init, args.fragment_media):
            with sample.open('rb') as input_file:
                while chunk := input_file.read(1024 * 1024):
                    output.write(chunk)
    result = probe(combined, 'packet=stream_index,size')
    assert any(int(packet.get('size', 0)) > 0 and packet.get('stream_index') == 1
               for packet in result.get('packets', []))
print('FFmpeg common encryption and MOV regressions passed')
