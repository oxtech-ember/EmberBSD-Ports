/* SPDX-License-Identifier: BSD-2-Clause */
/* Origin: EmberBSD (AI-assisted). Independent Linux input-name contracts. */
#include <stdio.h>
#include <string.h>
#include <linux/input-event-codes.h>
#include <libevdev/libevdev.h>

#define CHECK(condition) do { \
	if (!(condition)) { \
		fprintf(stderr, "FAIL: %s\n", #condition); \
		return 1; \
	} \
} while (0)

int
main(void)
{
	const char *name;

	CHECK(EV_KEY == 1);
	CHECK(BTN_LEFT == 0x110);
	CHECK(BTN_RIGHT == 0x111);
	CHECK(libevdev_event_code_from_name(1, "BTN_LEFT") == 0x110);
	CHECK(libevdev_event_code_from_name(1, "BTN_RIGHT") == 0x111);
	name = libevdev_event_code_get_name(1, 0x110);
	CHECK(name != NULL && strcmp(name, "BTN_LEFT") == 0);
	CHECK(libevdev_event_code_from_name(1, "BTN_DOES_NOT_EXIST") == -1);
	CHECK(libevdev_event_code_get_name(EV_MAX + 1, 0) == NULL);
	CHECK(libevdev_event_code_get_name(EV_KEY, KEY_MAX + 1) == NULL);
	CHECK(libevdev_event_type_get_max(EV_MAX + 1) == -1);
	CHECK(libevdev_event_type_from_name("EV_KEY") == 1);
	CHECK(libevdev_event_type_from_name("EV_NOT_REAL") == -1);
	CHECK(libevdev_property_from_name("INPUT_PROP_DIRECT") == 1);
	CHECK(libevdev_property_from_name("INPUT_PROP_NOT_REAL") == -1);
	puts("PASS: 14 input-name, ABI value and invalid-input contracts");
	return 0;
}
