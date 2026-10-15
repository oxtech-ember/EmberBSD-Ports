// SPDX-License-Identifier: MIT
#include "cpu.h"

#include <pthread.h>
#include <cstdio>

static pthread_barrier_t ready;

static void* query(void* pointer)
{
    int* result = static_cast<int*>(pointer);
    pthread_barrier_wait(&ready);
    *result = ncnn::get_cpu_count();
    for (int i = 0; i < 32; ++i)
        if (*result != ncnn::get_cpu_count())
            *result = -1;
    return 0;
}

int main()
{
    pthread_t threads[8];
    int counts[8] = {};
    if (pthread_barrier_init(&ready, 0, 9) != 0)
        return 1;
    for (int i = 0; i < 8; ++i)
        if (pthread_create(&threads[i], 0, query, &counts[i]) != 0)
            return 2;
    pthread_barrier_wait(&ready);
    for (int i = 0; i < 8; ++i)
        if (pthread_join(threads[i], 0) != 0)
            return 3;
    if (pthread_barrier_destroy(&ready) != 0)
        return 4;
    for (int i = 0; i < 8; ++i)
        if (counts[i] < 1 || counts[i] != counts[0])
            return 5;
    std::printf("Concurrent first CPU query: PASS (%d CPUs, 8 threads, 264 calls)\n", counts[0]);
    return 0;
}
