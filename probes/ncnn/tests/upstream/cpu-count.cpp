// SPDX-License-Identifier: MIT
#include "cpu.h"

#include <climits>
#include <cstdio>
#include <unistd.h>

int main()
{
    const long online = sysconf(_SC_NPROCESSORS_ONLN);
    const int reported = ncnn::get_cpu_count();
    if (online < 1 || online > INT_MAX)
    {
        std::fprintf(stderr, "The kernel CPU count is not a positive int: %ld\n", online);
        return 1;
    }
    std::printf("kernel_online=%ld ncnn_logical=%d ncnn_physical=%d\n",
                online, reported, ncnn::get_physical_cpu_count());
    if (reported != online)
    {
        std::fprintf(stderr, "The ncnn logical CPU count differs from sysconf\n");
        return 2;
    }
#if defined(__NetBSD__)
    ncnn::CpuSet unavailable;
    if (ncnn::set_cpu_thread_affinity(unavailable) != -1)
    {
        std::fprintf(stderr, "Unsupported NetBSD affinity must report failure\n");
        return 3;
    }
#if defined(__aarch64__)
    if (!ncnn::cpu_support_arm_neon() || !ncnn::cpu_support_arm_vfpv4()
        || ncnn::cpu_support_arm_asimdhp() || ncnn::cpu_support_arm_asimddp()
        || ncnn::cpu_support_arm_asimdfhm() || ncnn::cpu_support_arm_bf16()
        || ncnn::cpu_support_arm_i8mm() || ncnn::cpu_support_arm_sve()
        || ncnn::cpu_support_arm_sve2())
    {
        std::fprintf(stderr, "Unexpected baseline AArch64 feature profile\n");
        return 4;
    }
#endif
#endif
    std::puts("CPU source contract: PASS");
    return 0;
}
