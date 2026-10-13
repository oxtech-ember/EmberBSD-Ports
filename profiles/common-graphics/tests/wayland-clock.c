/* SPDX-License-Identifier: BSD-2-Clause */
/* Origin: EmberBSD contributors (AI-assisted). Actual WSI clock mappings. */
#include <vulkan/vulkan_core.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <time.h>

/* Test both feature profiles regardless of the build host's clock API. */
#ifdef TEST_RAW_CLOCK
#ifndef CLOCK_MONOTONIC_RAW
/* Model an available, distinct ID without reading that clock. */
#define CLOCK_MONOTONIC_RAW CLOCK_PROCESS_CPUTIME_ID
#endif
#else
#undef CLOCK_MONOTONIC_RAW
#endif
#include "wayland-clock-source.h"

#define CHECK(c) do { if (!(c)) { \
	fprintf(stderr, "FAIL line %d: %s\n", __LINE__, #c); abort(); \
} } while (0)

int
main(void)
{
	CHECK(clock_id_to_vk_time_domain(CLOCK_MONOTONIC) ==
	    VK_TIME_DOMAIN_CLOCK_MONOTONIC_KHR);
	CHECK(vk_time_domain_to_clock_id(VK_TIME_DOMAIN_CLOCK_MONOTONIC_KHR) ==
	    CLOCK_MONOTONIC);
	CHECK(presentation_clock_supported(CLOCK_MONOTONIC));
	CHECK(!presentation_clock_supported(CLOCK_REALTIME));
	CHECK(!presentation_clock_supported((clockid_t)2147483645));
	CHECK(clock_id_to_vk_time_domain((clockid_t)2147483645) ==
	    VK_TIME_DOMAIN_CLOCK_MONOTONIC_KHR);
	CHECK(vk_time_domain_to_clock_id(VK_TIME_DOMAIN_DEVICE_KHR) == 0);
#ifdef TEST_RAW_CLOCK
	CHECK(presentation_clock_supported(CLOCK_MONOTONIC_RAW));
	CHECK(clock_id_to_vk_time_domain(CLOCK_MONOTONIC_RAW) ==
	    VK_TIME_DOMAIN_CLOCK_MONOTONIC_RAW_KHR);
	CHECK(vk_time_domain_to_clock_id(VK_TIME_DOMAIN_CLOCK_MONOTONIC_RAW_KHR) ==
	    CLOCK_MONOTONIC_RAW);
#else
	CHECK(!presentation_clock_supported((clockid_t)2147483646));
	CHECK(vk_time_domain_to_clock_id(VK_TIME_DOMAIN_CLOCK_MONOTONIC_RAW_KHR) == 0);
#endif
	puts("PASS: actual Wayland clock conversion and presentation admission");
	return 0;
}
