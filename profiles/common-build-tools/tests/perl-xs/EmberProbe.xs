/* SPDX-License-Identifier: BSD-2-Clause */
/* Origin: EmberBSD (AI-assisted), installed CORE headers and native XS ABI. */
#include "EXTERN.h"
#include "perl.h"
#include "XSUB.h"

MODULE = EmberProbe    PACKAGE = EmberProbe
PROTOTYPES: DISABLE

UV
roundtrip(value)
        UV value
    CODE:
        RETVAL = value;
    OUTPUT:
        RETVAL

void
reject()
    CODE:
        croak("Ember XS exception");
