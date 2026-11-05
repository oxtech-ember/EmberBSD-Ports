# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Select common codec libraries for both Chromium toolchain roles."""

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
