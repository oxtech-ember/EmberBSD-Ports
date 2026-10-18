/* SPDX-License-Identifier: BSD-2-Clause */
/* Origin: EmberBSD (AI-assisted). The public header must declare its types. */
#include "stringop.h"

char *
header_contract(const char *format, va_list arguments)
{

	return vformat_str(format, arguments);
}
