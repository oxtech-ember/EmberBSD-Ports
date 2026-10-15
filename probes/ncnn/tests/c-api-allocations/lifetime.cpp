// SPDX-License-Identifier: MIT
#include "c_api.h"

#include <cstdio>
#include <cstring>

static bool check_values(ncnn_mat_t mat, int number, int dimensions)
{
    if (!mat || ncnn_mat_get_dims(mat) != dimensions)
        return false;
    const float* data = static_cast<const float*>(ncnn_mat_get_data(mat));
    const int channels = dimensions == 3 ? 2 : 1;
    const size_t stride = dimensions == 3 ? ncnn_mat_get_cstep(mat) : 0;
    for (int channel = 0; channel < channels; ++channel)
        for (int i = 0; i < 6; ++i)
            if (data[channel * stride + i] != number * 100 + channel * 6 + i + 1)
                return false;
    return true;
}

static int baseline_first()
{
    ncnn_mat_t original = ncnn_mat_create_1d(6, 0);
    if (!original)
        return 1;
    ncnn_mat_fill_float(original, 7.f);
    ncnn_modelbin_t model = ncnn_modelbin_create_from_mat_array(&original, 1);
    if (!model)
        return 2;
    ncnn_mat_t loaded = model->load_1d(model, 6, 0);
    if (!loaded || ncnn_mat_get_w(loaded) != 6)
        return 3;
    ncnn_mat_destroy(loaded);
    ncnn_modelbin_destroy(model);
    ncnn_mat_destroy(original);
    return 0;
}

static ncnn_mat_t callback_load(const ncnn_modelbin_t, int count, int)
{
    ncnn_mat_t mat = ncnn_mat_create_1d(count, 0);
    if (mat)
        ncnn_mat_fill_float(mat, 123.f);
    return mat;
}

int main(int argc, char** argv)
{
    if (argc == 2 && std::strcmp(argv[1], "--baseline-first") == 0)
        return baseline_first();
    if (argc != 1)
        return 4;
    ncnn_mat_t originals[6];
    for (int number = 0; number < 6; ++number)
    {
        const int count = number % 3 == 2 ? 12 : 6;
        originals[number] = ncnn_mat_create_1d(count, 0);
        if (!originals[number])
            return 5;
        float* values = static_cast<float*>(ncnn_mat_get_data(originals[number]));
        for (int i = 0; i < count; ++i)
            values[i] = static_cast<float>(number * 100 + i + 1);
    }
    ncnn_modelbin_t model = ncnn_modelbin_create_from_mat_array(originals, 6);
    if (!model)
        return 6;
    for (int number = 0; number < 6; ++number)
        ncnn_mat_destroy(originals[number]);
    for (int number = 0; number < 6; ++number)
    {
        const int dimensions = number % 3 + 1;
        ncnn_mat_t loaded = dimensions == 1 ? model->load_1d(model, 6, 0)
            : dimensions == 2 ? model->load_2d(model, 2, 3, 0)
            : model->load_3d(model, 2, 3, 2, 0);
        if (!check_values(loaded, number, dimensions))
            return 7;
        ncnn_mat_destroy(loaded);
    }
    ncnn_mat_t exhausted = model->load_1d(model, 1, 0);
    if (!exhausted || ncnn_mat_get_dims(exhausted) != 0)
        return 8;
    ncnn_mat_destroy(exhausted);
    ncnn_modelbin_destroy(model);
    model = ncnn_modelbin_create_from_mat_array(0, 0);
    if (!model)
        return 9;
    ncnn_mat_t empty = model->load_3d(model, 1, 1, 1, 0);
    if (!empty || ncnn_mat_get_dims(empty) != 0)
        return 10;
    ncnn_mat_destroy(empty);
    model->load_1d = callback_load;
    ncnn_mat_t callback = model->load_2d(model, 2, 3, 0);
    if (!callback || ncnn_mat_get_dims(callback) != 2)
        return 11;
    const float* callback_data = static_cast<const float*>(ncnn_mat_get_data(callback));
    for (int i = 0; i < 6; ++i)
        if (callback_data[i] != 123.f)
            return 12;
    ncnn_mat_destroy(callback);
    ncnn_modelbin_destroy(model);
    std::puts("C API retained weight lifetime: PASS (6 arrays, 48 values, empty, exhausted and callback dispatch)");
    return 0;
}
