// SPDX-License-Identifier: BSD-2-Clause
// Origin: EmberBSD (AI-assisted). Fixed-header rejection through real APIs.
#include "whisper.h"
#include <algorithm>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <fstream>
#include <string>
#include <vector>

struct input_buffer {
    const unsigned char *data;
    size_t size;
    size_t offset;
    unsigned closes;
};

static bool rejected(whisper_context *ctx) {
    if (ctx == nullptr) return true;
    whisper_free(ctx);
    return false;
}

int main(int argc, char **argv) {
    if (argc != 3) return 2;
    std::ifstream source(argv[1], std::ios::binary);
    std::vector<unsigned char> header(56);
    if (!source.read(reinterpret_cast<char *>(header.data()), header.size())) return 2;
    whisper_context_params params = whisper_context_default_params();
    params.use_gpu = false;
    if (!rejected(whisper_init_from_buffer_with_params_no_state(nullptr, 4, params))) return 1;
    for (size_t size = 0; size < header.size(); ++size) {
        if (!rejected(whisper_init_from_buffer_with_params_no_state(header.data(), size, params))) return 1;
        const std::string path = std::string(argv[2]) + "/header-" + std::to_string(size) + ".bin";
        {
            std::ofstream file(path, std::ios::binary);
            file.write(reinterpret_cast<const char *>(header.data()), size);
            file.close();
            if (!file) return 2;
        }
        if (!rejected(whisper_init_from_file_with_params_no_state(path.c_str(), params))) return 1;
        input_buffer input{header.data(), size, 0, 0};
        whisper_model_loader loader{};
        loader.context = &input;
        loader.read = [](void *context, void *output, size_t requested) -> size_t {
            auto &buffer = *static_cast<input_buffer *>(context);
            const size_t count = std::min(requested, buffer.size - buffer.offset);
            if (count != 0) std::memcpy(output, buffer.data + buffer.offset, count);
            buffer.offset += count;
            return count;
        };
        loader.eof = [](void *context) { auto &buffer = *static_cast<input_buffer *>(context); return buffer.offset == buffer.size; };
        loader.close = [](void *context) { ++static_cast<input_buffer *>(context)->closes; };
        if (!rejected(whisper_init_with_params_no_state(&loader, params)) || input.closes != 1) return 1;
    }
    std::puts("PASS: 56 incomplete fixed headers through file, buffer and callback APIs; one callback close; NULL buffer rejected");
    return 0;
}
