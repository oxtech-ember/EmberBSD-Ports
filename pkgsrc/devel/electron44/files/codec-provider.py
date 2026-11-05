# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Select common codec libraries for both Chromium toolchain roles."""

import re
from pathlib import Path

PROVIDERS = {
    'dav1d': ('multimedia/dav1d', 'dav1d', (1, 5, 4, 0), ('libdav1d',), ('dav1d',),
              tuple('include/dav1d/' + n for n in ('common.h', 'data.h', 'dav1d.h', 'headers.h', 'picture.h', 'version.h'))),
    'aom': ('multimedia/libaom', 'libaom', (3, 15, 2, 0), ('libaom',), ('aom',),
            tuple('include/aom/' + n for n in ('aom.h', 'aom_codec.h', 'aom_decoder.h', 'aom_encoder.h',
                  'aom_ext_ratectrl.h', 'aom_tpl.h', 'aom_external_partition.h', 'aom_frame_buffer.h', 'aom_image.h', 'aom_integer.h', 'aomcx.h', 'aomdx.h'))),
    'vpx': ('multimedia/libvpx', 'libvpx', (1, 17, 0, 0), ('libvpx',), ('vpx',),
            tuple('include/vpx/' + n for n in ('vp8.h', 'vp8cx.h', 'vp8dx.h', 'vpx_codec.h', 'vpx_decoder.h',
                  'vpx_encoder.h', 'vpx_ext_ratectrl.h', 'vpx_tpl.h', 'vpx_frame_buffer.h', 'vpx_image.h', 'vpx_integer.h'))),
    'opus': ('audio/libopus', 'libopus', (1, 6, 1, 1), ('libopus',), ('opus',),
             tuple('include/opus/' + n for n in ('opus.h', 'opus_defines.h', 'opus_multistream.h', 'opus_types.h'))),
    'flac': ('audio/flac', 'flac', (1, 5, 0, 1), ('libFLAC',), ('flac',),
             tuple('include/FLAC/' + n for n in ('all.h', 'assert.h', 'callback.h', 'export.h', 'format.h',
                   'metadata.h', 'ordinals.h', 'stream_decoder.h', 'stream_encoder.h'))),
}


def select(image, controller, options, sdk, native, environment, buildlink):
    if not getattr(options, 'shared_codecs', False):
        return {}
    return image.select_roles(controller, options, sdk, native, environment, buildlink,
                              PROVIDERS, {'emberbsd_common_codecs': True},
                              'EMBERBSD_CODEC_SOURCE_SHA256')


OPENH264_PROVIDER = {
    'openh264': ('multimedia/openh264', 'openh264', (2, 7, 0, 0),
                 ('libopenh264',), ('openh264',),
                 tuple('include/wels/' + name for name in
                       ('codec_api.h', 'codec_app_def.h', 'codec_def.h', 'codec_ver.h'))),
}


def select_openh264(image, controller, options, sdk, native, environment, buildlink):
    if not getattr(options, 'shared_openh264', False):
        return {}
    return image.select_roles(controller, options, sdk, native, environment, buildlink,
                              OPENH264_PROVIDER, {'emberbsd_common_openh264': True, 'rtc_system_openh264': False},
                              'EMBERBSD_OPENH264_SOURCE_SHA256')


PFFFT_PROVIDER = {
    'pffft': ('audio/pffft', 'pffft', (1, 1, 0, 2),
              ('libpffft',), ('pffft',), ('include/pffft/pffft.h',)),
}


def select_pffft(image, controller, options, sdk, native, environment, buildlink):
    if not getattr(options, 'shared_pffft', False):
        return {}
    return image.select_roles(controller, options, sdk, native, environment, buildlink,
                              PFFFT_PROVIDER, {'emberbsd_common_pffft': True},
                              'EMBERBSD_PFFFT_SOURCE_SHA256')


EXPAT_PROVIDER = {
    'expat': ('textproc/expat', 'expat', (2, 10, 0, 1),
              ('libexpat',), ('expat',),
              ('include/expat.h', 'include/expat_external.h', 'include/expat_config.h')),
}


def select_expat(image, controller, options, sdk, native, environment, buildlink):
    if not getattr(options, 'shared_expat', False):
        return {}
    values = image.select_roles(controller, options, sdk, native, environment, buildlink,
                                EXPAT_PROVIDER, {'emberbsd_common_expat': True},
                                'EMBERBSD_EXPAT_SOURCE_SHA256')
    for role in ('host', 'target'):
        configs = [Path(x) for x in values['emberbsd_expat_' + role + '_inputs']
                   if x.endswith('/include/expat_config.h')]
        controller.require(len(configs) == 1, 'selected Expat configuration is missing')
        config = configs[0].read_text()
        for macro, expected in (('XML_DTD', '1'), ('XML_GE', '1'), ('XML_NS', '1'),
                                ('XML_CONTEXT_BYTES', '1024')):
            controller.require(re.search(r'^#\s*define\s+' + macro + r'\s+' + expected + r'\s*$', config, re.M),
                               'selected Expat configuration lacks ' + macro)
    return values
