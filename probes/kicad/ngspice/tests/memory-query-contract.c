/* SPDX-License-Identifier: BSD-2-Clause */
/* Origin: EmberBSD (AI-assisted). Compile with the three real query modules. */
#include <stdio.h>
#include <stdint.h>
#include <unistd.h>
#include "ngspice/config.h"
#if defined(__NetBSD__)
#include <sys/types.h>
#include <sys/sysctl.h>
#endif

unsigned long long getMemorySize(void);
unsigned long long getAvailableMemorySize(void);
unsigned long long getPeakRSS(void);
unsigned long long getCurrentRSS(void);

int
main(void)
{
    unsigned long long total = getMemorySize();
    unsigned long long available = getAvailableMemorySize();
    unsigned long long peak = getPeakRSS();
    unsigned long long current = getCurrentRSS();
    printf("total=%llu available=%llu peak=%llu current=%llu\n",
        total, available, peak, current);
#if defined(__NetBSD__)
    int mib[] = { CTL_HW, HW_PHYSMEM64 };
    int64_t physical = 0;
    size_t length = sizeof(physical);
    if (sysctl(mib, 2, &physical, &length, NULL, 0) != 0 ||
        length != sizeof(physical) || physical <= 0) {
        perror("independent HW_PHYSMEM64 query");
        return 2;
    }
    if (total != (unsigned long long)physical || available != total || current != 0)
        return 1;
#if defined(HAVE_GETRUSAGE)
    if (peak == 0)
        return 1;
#else
    if (peak != 0)
        return 1;
#endif
    /* OpenMP configure omits getrusage; the selected BSD RSS paths return zero. */
    puts("PASS: NetBSD total matches sysctl; inherited available=total and RSS limits retained");
#else
    if (total == 0 || available == 0 || available > total || peak == 0 || current == 0)
        return 1;
    puts("PASS: native procfs memory queries return positive values");
#endif
    return 0;
}
