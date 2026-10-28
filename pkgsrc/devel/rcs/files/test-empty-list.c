/* SPDX-License-Identifier: BSD-2-Clause
 * Copyright (c) 2026 EmberBSD contributors.
 * Origin: EmberBSD (AI-assisted).
 */
#include "base.h"
#include "b-esds.h"

void
check_empty_lists(void *entry, struct divvy *storage)
{
	(void)prepend(entry, NULL, storage);
	(void)wprepend(entry, NULL, storage);
}
