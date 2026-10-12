/* SPDX-License-Identifier: BSD-2-Clause
 * Origin: EmberBSD (AI-assisted).
 * Compile against the actual patched libvpx source and generated config.
 */
#include <sys/types.h>
#include <sys/sysctl.h>
#include <aarch64/armreg.h>
#include <assert.h>
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static int scenario = -1;
static int
fixture_sysctl(const char *name, void *out, size_t *size,
    const void *newp, size_t newlen)
{
	if (scenario == -1)
		return sysctlbyname(name, out, size, newp, newlen);
	if (strcmp(name, "hw.ncpu") == 0) {
		if (scenario == 1) { errno = ENOENT; return -1; }
		assert(*size >= sizeof(int));
		*(int *)out = scenario == 3 ? 0 : 2;
		*size = scenario == 2 ? sizeof(int) - 1 : sizeof(int);
		return 0;
	}
	assert(strcmp(name, "machdep.cpu0.cpu_id") == 0 ||
	    strcmp(name, "machdep.cpu1.cpu_id") == 0);
	const int cpu = name[11] - '0';
	if (scenario == 4 && cpu == 1) { errno = ENOENT; return -1; }
	struct aarch64_sysctl_cpu_id id;
	memset(&id, 0, sizeof(id));
	id.ac_aa64isar0 = __SHIFTIN(1, ID_AA64ISAR0_EL1_CRC32) |
	    __SHIFTIN(1, ID_AA64ISAR0_EL1_DP);
	id.ac_aa64isar1 = __SHIFTIN(1, ID_AA64ISAR1_EL1_I8MM);
	/* SVE hardware bits must not establish OS support. */
	id.ac_aa64pfr0 = __SHIFTIN(1, ID_AA64PFR0_EL1_SVE);
	id.ac_aa64zfr0 = 1;
	if (scenario == 6 && cpu == 1) id.ac_aa64isar1 = 0;
	if (scenario == 7 && cpu == 1) id.ac_aa64isar0 = 0;
	if (scenario == 8) {
		id.ac_aa64isar0 = UINT64_MAX;
		id.ac_aa64isar1 = UINT64_MAX;
	}
	assert(*size >= sizeof(id));
	memcpy(out, &id, sizeof(id));
	*size = scenario == 5 && cpu == 1 ? 1 : sizeof(id);
	return 0;
}

#define sysctlbyname fixture_sysctl
#include "vpx_ports/aarch64_cpudetect.c"
#undef sysctlbyname

#if !CONFIG_RUNTIME_CPU_DETECT || !HAVE_NEON || \
    !HAVE_NEON_DOTPROD || !HAVE_NEON_I8MM
#error Test requires the full AArch64 runtime dispatch build
#endif

int
main(void)
{
	unsetenv("VPX_SIMD_CAPS");
	unsetenv("VPX_SIMD_CAPS_MASK");
	printf("actual_cpu_caps=%d\n", arm_cpu_caps());
	scenario = 0;
	assert(arm_cpu_caps() == 7);
	for (scenario = 1; scenario <= 5; scenario++)
		assert(arm_cpu_caps() == HAS_NEON);
	scenario = 6;
	assert(arm_cpu_caps() == 3);
	scenario = 7;
	assert(arm_cpu_caps() == HAS_NEON);
	scenario = 8;
	assert(arm_cpu_caps() == HAS_NEON);
	scenario = 0;
	setenv("VPX_SIMD_CAPS_MASK", "1", 1);
	assert(arm_cpu_caps() == HAS_NEON);
	setenv("VPX_SIMD_CAPS", "0", 1);
	assert(arm_cpu_caps() == 0);
	unsetenv("VPX_SIMD_CAPS");
	unsetenv("VPX_SIMD_CAPS_MASK");
	puts("PASS: full dispatch, heterogeneous CPUs, missing/truncated sysctl, reserved bits, SVE safety and environment masks");
	return 0;
}
