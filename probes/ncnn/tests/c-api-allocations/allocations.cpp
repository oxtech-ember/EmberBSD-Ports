// SPDX-License-Identifier: MIT
#include "c_api.h"

#include <cerrno>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <csignal>
#include <sys/resource.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <unistd.h>

static bool armed;
static int failures;

extern "C" void* __real_malloc(size_t);

extern "C" void* __wrap_malloc(size_t size)
{
    if (armed)
    {
        armed = false;
        ++failures;
        errno = ENOMEM;
        return 0;
    }
    return __real_malloc(size);
}

static ncnn_layer_t create_custom(void*)
{
    return ncnn_layer_create();
}

static void destroy_custom(ncnn_layer_t layer, void*)
{
    ncnn_layer_destroy(layer);
}

static int load_custom(ncnn_net_t net)
{
    const int graph[] = {7767517, 1, 1, 256, 0, 1, 0, -233};
    const unsigned char* memory = reinterpret_cast<const unsigned char*>(graph);
    ncnn_datareader_t reader = ncnn_datareader_create_from_memory(&memory);
    if (!reader)
        return -2;
    const int result = ncnn_net_load_param_bin_datareader(net, reader);
    ncnn_datareader_destroy(reader);
    return result;
}

static int check_case(int number)
{
    ncnn_datareader_t reader = 0;
    ncnn_net_t net = 0;
    FILE* fp = 0;
    unsigned char data[16] = {};
    const unsigned char* memory = data;
    if (number == 3 && !(fp = std::tmpfile()))
        return 10;
    if (number == 5 && !(reader = ncnn_datareader_create()))
        return 11;
    if ((number == 11 || number == 12) && !(net = ncnn_net_create()))
        return 12;
    const int relu = ncnn_layer_type_to_index("ReLU");
    bool rejected = false;
    const int previous_failures = failures;
    armed = true;
    switch (number)
    {
    case 0: rejected = ncnn_allocator_create_pool_allocator() == 0; break;
    case 1: rejected = ncnn_allocator_create_unlocked_pool_allocator() == 0; break;
    case 2: rejected = ncnn_datareader_create() == 0; break;
    case 3: rejected = ncnn_datareader_create_from_stdio(fp) == 0; break;
    case 4: rejected = ncnn_datareader_create_from_memory(&memory) == 0; break;
    case 5: rejected = ncnn_modelbin_create_from_datareader(reader) == 0; break;
    case 6: rejected = ncnn_modelbin_create_from_mat_array(0, 0) == 0; break;
    case 7: rejected = ncnn_layer_create() == 0; break;
    case 8: rejected = ncnn_layer_create_by_typeindex(relu) == 0; break;
    case 9: rejected = ncnn_layer_create_by_type("ReLU") == 0; break;
    case 10: rejected = ncnn_net_create() == 0; break;
    case 11:
        ncnn_net_register_custom_layer_by_type(net, "AllocationFailure", create_custom, destroy_custom, 0);
        rejected = net->custom_layer_factory == 0;
        break;
    case 12:
        ncnn_net_register_custom_layer_by_typeindex(net, 256, create_custom, destroy_custom, 0);
        rejected = net->custom_layer_factory == 0;
        break;
    default: return 13;
    }
    if (armed || failures != previous_failures + 1 || !rejected)
        return 14;
    if (number == 11 || number == 12)
    {
        if (load_custom(net) == 0)
            return 20;
        if (number == 11)
            ncnn_net_register_custom_layer_by_type(net, "AllocationFailure", create_custom, destroy_custom, 0);
        else
            ncnn_net_register_custom_layer_by_typeindex(net, 256, create_custom, destroy_custom, 0);
        if (!net->custom_layer_factory || load_custom(net) != 0)
            return 21;
    }
    if (reader)
        ncnn_datareader_destroy(reader);
    if (net)
        ncnn_net_destroy(net);
    if (fp && std::fclose(fp) != 0)
        return 15;
    std::printf("C API malloc failure %d: PASS\n", number);
    return 0;
}

int main(int argc, char** argv)
{
    if (argc == 2 && std::strcmp(argv[1], "--baseline") == 0)
    {
        struct rlimit no_core = {0, 0};
        if (setrlimit(RLIMIT_CORE, &no_core) != 0)
            return 16;
        for (int number = 0; number < 13; ++number)
        {
            const pid_t child = fork();
            if (child < 0)
                return 17;
            if (child == 0)
                _exit(check_case(number));
            int status = 0;
            if (waitpid(child, &status, 0) != child || !WIFSIGNALED(status)
                || WTERMSIG(status) != SIGSEGV)
            {
                std::fprintf(stderr, "Baseline case %d did not expose the null write (status %d)\n", number, status);
                return 18;
            }
            std::printf("Baseline malloc failure %d: detected SIGSEGV\n", number);
        }
        return 0;
    }
    if (argc != 1)
        return 19;
    for (int number = 0; number < 13; ++number)
    {
        const int result = check_case(number);
        if (result != 0)
            return result;
    }
    return 0;
}
