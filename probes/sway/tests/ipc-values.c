/* SPDX-License-Identifier: MIT
 * Origin: EmberBSD (AI-assisted). Check the actual Sway protocol header.
 */
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include "ipc.h"

_Static_assert(sizeof(enum ipc_command_type) == sizeof(uint32_t), "IPC enum width");
_Static_assert(IPC_EVENT_WORKSPACE == UINT32_C(0x80000000), "workspace wire flag");
_Static_assert(IPC_EVENT_INPUT == UINT32_C(0x80000015), "input wire flag");

int
main(void)
{
	const uint32_t events[] = {
		IPC_EVENT_WORKSPACE, IPC_EVENT_OUTPUT, IPC_EVENT_MODE,
		IPC_EVENT_WINDOW, IPC_EVENT_BARCONFIG_UPDATE, IPC_EVENT_BINDING,
		IPC_EVENT_SHUTDOWN, IPC_EVENT_TICK,
		IPC_EVENT_BAR_STATE_UPDATE, IPC_EVENT_INPUT
	};
	const unsigned int ids[] = {0, 1, 2, 3, 4, 5, 6, 7, 20, 21};
	for (unsigned int i = 0; i < sizeof(ids) / sizeof(ids[0]); i++) {
		assert(events[i] == (UINT32_C(0x80000000) | ids[i]));
		assert(event_mask(events[i]) == (UINT32_C(1) << ids[i]));
	}
	/* Exercise the formerly undefined signed mask shift at runtime too. */
	volatile uint32_t last = UINT32_C(0x8000001f);
	assert(event_mask(last) == UINT32_C(0x80000000));
	assert(IPC_COMMAND == 0 && IPC_GET_SEATS == 101);
	puts("PASS: 10 event wire values, 11 masks, enum width and command values");
	return 0;
}
