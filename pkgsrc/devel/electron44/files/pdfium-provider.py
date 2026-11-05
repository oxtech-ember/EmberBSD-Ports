# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Select common PDFium image libraries for both GN roles."""

PROVIDERS = {
    'lcms2': ('graphics/lcms2', 'lcms2', (2, 19, 1, 2), ('liblcms2',), ('lcms2',),
              ('include/lcms2.h', 'include/lcms2_plugin.h')),
    'openjpeg': ('graphics/openjpeg', 'openjpeg', (2, 5, 4, 1), ('libopenjp2',), ('libopenjp2',),
                 ('include/openjpeg-2.5/openjpeg.h', 'include/openjpeg-2.5/opj_config.h')),
    'tiff': ('graphics/tiff', 'tiff', (4, 7, 2, 2), ('libtiff',), ('libtiff-4',),
             ('include/tiff.h', 'include/tiffconf.h', 'include/tiffio.h', 'include/tiffvers.h')),
}


def select(image, controller, options, sdk, native, environment, buildlink):
    if not getattr(options, 'shared_pdf_libraries', False):
        return {}
    result = image.select_roles(controller, options, sdk, native, environment, buildlink, PROVIDERS,
                                {'emberbsd_common_pdf': True, 'use_system_lcms2': True,
                                 'use_system_libopenjpeg2': True, 'use_system_libtiff': True},
                                'EMBERBSD_PDF_SOURCE_SHA256')
    options.pdf_identity = environment['EMBERBSD_PDF_SOURCE_SHA256']
    return result
