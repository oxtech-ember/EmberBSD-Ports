// SPDX-License-Identifier: MIT
#include "c_api.h"
#include "layer.h"
#include "mat.h"
#include "modelbin.h"
#include "option.h"

#include <cstdio>
#include <cstring>
#include <csignal>
#include <sys/resource.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <unistd.h>
#include <vector>

static int mode;

static ncnn_mat_t output(float value)
{
    ncnn_mat_t mat = ncnn_mat_create_1d(2, 0);
    if (mat)
        ncnn_mat_fill_float(mat, value);
    return mat;
}

static int forward_one(const ncnn_layer_t, const ncnn_mat_t, ncnn_mat_t* top, const ncnn_option_t)
{
    if (mode == 1 || mode == 3)
        *top = output(8.f);
    return mode <= 1 ? -77 : 0;
}

static int forward_many(const ncnn_layer_t, const ncnn_mat_t* bottom, int n, ncnn_mat_t* top, int n2, const ncnn_option_t)
{
    if (mode == 8)
        return n == 0 && n2 == 0 && !bottom && !top ? 0 : -66;
    if (n != 1 || n2 != 2 || !bottom || !top)
        return -66;
    if (mode == 5 || mode == 6 || mode == 7 || mode == 17)
        top[0] = output(8.f);
    if (mode == 7 || mode == 17)
        top[1] = output(9.f);
    return mode == 4 || mode == 5 || mode == 17 ? -77 : 0;
}

static int inplace_many(const ncnn_layer_t, ncnn_mat_t* blobs, int n, const ncnn_option_t)
{
    return n == 0 && !blobs ? 0 : -66;
}

static ncnn_mat_t no_weight_1d(const ncnn_modelbin_t, int, int) { return 0; }
static ncnn_mat_t no_weight_2d(const ncnn_modelbin_t, int, int, int) { return 0; }
static ncnn_mat_t no_weight_3d(const ncnn_modelbin_t, int, int, int, int) { return 0; }

static int check_case(int number)
{
    mode = number;
    if (number >= 10 && number <= 15)
    {
        ncnn_datareader_t reader = 0;
        ncnn_modelbin_t model = 0;
        if (number <= 12)
        {
            reader = ncnn_datareader_create();
            if (!reader)
                return 10;
            model = ncnn_modelbin_create_from_datareader(reader);
        }
        else
            model = ncnn_modelbin_create_from_mat_array(0, 0);
        if (!model)
            return 11;
        model->load_1d = no_weight_1d;
        model->load_2d = no_weight_2d;
        model->load_3d = no_weight_3d;
        const ncnn::ModelBin* adapter = static_cast<const ncnn::ModelBin*>(model->pthis);
        const int dimensions = (number - 10) % 3 + 1;
        const ncnn::Mat result = dimensions == 1 ? adapter->load(1, 0)
            : dimensions == 2 ? adapter->load(1, 1, 0)
            : adapter->load(1, 1, 1, 0);
        const bool empty = result.empty();
        ncnn_modelbin_destroy(model);
        if (reader)
            ncnn_datareader_destroy(reader);
        return empty ? 0 : 90;
    }
    ncnn_layer_t raw = ncnn_layer_create();
    if (!raw)
        return 12;
    raw->forward_1 = forward_one;
    raw->forward_n = forward_many;
    raw->forward_inplace_n = inplace_many;
    const ncnn::Layer* adapter = static_cast<const ncnn::Layer*>(raw->pthis);
    ncnn::Option options;
    ncnn::Mat input(2);
    input.fill(1.f);
    bool correct = false;
    if (number <= 3)
    {
        ncnn::Mat result(2);
        result.fill(19.f);
        const int status = adapter->forward(input, result, options);
        const int expected = number <= 1 ? -77 : number == 2 ? -100 : 0;
        correct = status == expected && result[0] == (number == 3 ? 8.f : 19.f);
    }
    else if (number == 9 || number == 16)
    {
        std::vector<ncnn::Mat> empty;
        correct = adapter->forward_inplace(empty, options) == 0;
    }
    else
    {
        std::vector<ncnn::Mat> inputs;
        std::vector<ncnn::Mat> results;
        if (number != 8)
        {
            inputs.push_back(input);
            results.resize(2);
            for (int i = 0; i < 2; ++i)
            {
                results[i].create(2);
                results[i].fill(19.f + i);
            }
        }
        const int status = adapter->forward(inputs, results, options);
        const int expected = number == 4 || number == 5 || number == 17 ? -77
            : number == 6 ? -100 : 0;
        correct = status == expected;
        for (size_t i = 0; i < results.size(); ++i)
            correct = correct && results[i][0] == (number == 7 ? 8.f + i : 19.f + i);
    }
    ncnn_layer_destroy(raw);
    return correct ? 0 : 90;
}

int main(int argc, char** argv)
{
    if (argc == 2 && std::strcmp(argv[1], "--baseline") == 0)
    {
        struct rlimit no_core = {0, 0};
        if (setrlimit(RLIMIT_CORE, &no_core) != 0)
            return 13;
        const int cases[] = {0, 1, 2, 4, 5, 6, 10, 11, 12, 13, 14, 15, 17};
        for (size_t i = 0; i < sizeof(cases) / sizeof(cases[0]); ++i)
        {
            const pid_t child = fork();
            if (child < 0)
                return 14;
            if (child == 0)
                _exit(check_case(cases[i]));
            int status = 0;
            if (waitpid(child, &status, 0) != child)
                return 15;
            const bool null_write = WIFSIGNALED(status) && WTERMSIG(status) == SIGSEGV;
            const bool wrong_result = WIFEXITED(status) && WEXITSTATUS(status) == 90;
            if (!null_write && !wrong_result)
            {
                std::fprintf(stderr, "Baseline callback case %d did not expose its failure (status %d)\n", cases[i], status);
                return 16;
            }
            std::printf("Baseline callback case %d: detected %s\n", cases[i], null_write ? "SIGSEGV" : "changed output");
        }
        return 0;
    }
    if (argc != 1)
        return 17;
    for (int number = 0; number < 18; ++number)
    {
        const int status = check_case(number);
        if (status != 0)
            return status;
    }
    std::puts("C API callback failures: PASS (18 controls, retained outputs, owned-handle cleanup)");
    return 0;
}
