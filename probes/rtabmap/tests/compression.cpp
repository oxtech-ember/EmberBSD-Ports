// SPDX-License-Identifier: MIT
// AI-assisted regressions through the real RTAB-Map compression API.
#include <rtabmap/core/Compression.h>
#include <rtabmap/core/rvl_codec.h>
#include <opencv2/core.hpp>
#include <zlib.h>

#include <algorithm>
#include <array>
#include <cstring>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

namespace {
void require(bool condition, const char* message)
{
    if (!condition) throw std::runtime_error(message);
}

cv::Mat input(int count)
{
    cv::Mat data(1, count, CV_8UC1);
    for (int i = 0; i < count; ++i) data.data[i] = static_cast<unsigned char>(i * 37 + count);
    return data;
}

void same_data(const cv::Mat& actual, const cv::Mat& expected)
{
    require(actual.type() == expected.type() && actual.size() == expected.size(),
        "data round trip changed matrix layout");
    require(actual.isContinuous() && std::memcmp(actual.data, expected.data,
        expected.total() * expected.elemSize()) == 0, "data round trip changed values");
}

std::array<int, 3> trailer(const unsigned char* data, std::size_t size)
{
    require(size >= 3 * sizeof(int), "missing matrix trailer");
    std::array<int, 3> result{};
    std::memcpy(result.data(), data + size - 3 * sizeof(int), 3 * sizeof(int));
    return result;
}

void data_round_trips(const std::string& mode)
{
    bool tested_unaligned = false;
    for (int count = 1; count <= 64; ++count) {
        const cv::Mat expected = input(count);
        if (mode == "data-vector") {
            const auto encoded = rtabmap::compressData(expected);
            require(trailer(encoded.data(), encoded.size()) == std::array<int, 3>{1, count, CV_8UC1},
                "vector trailer changed");
            tested_unaligned |= (encoded.size() - 3 * sizeof(int)) % alignof(int) != 0;
            same_data(rtabmap::uncompressData(encoded), expected);
        } else if (mode == "data-mat") {
            const cv::Mat encoded = rtabmap::compressData2(expected);
            const std::size_t size = encoded.total() * encoded.elemSize();
            require(trailer(encoded.data, size) == std::array<int, 3>{1, count, CV_8UC1},
                "Mat trailer changed");
            tested_unaligned |= (size - 3 * sizeof(int)) % alignof(int) != 0;
            same_data(rtabmap::uncompressData(encoded), expected);
        } else {
            // Build a valid fixture independently. Trailer access uses memcpy.
            uLongf compressed = compressBound(static_cast<uLong>(count));
            std::vector<unsigned char> encoded(compressed + 3 * sizeof(int));
            require(compress(encoded.data(), &compressed, expected.data,
                static_cast<uLong>(count)) == Z_OK, "independent zlib encoding failed");
            encoded.resize(compressed + 3 * sizeof(int));
            const std::array<int, 3> metadata{1, count, CV_8UC1};
            std::memcpy(encoded.data() + compressed, metadata.data(), 3 * sizeof(int));
            tested_unaligned |= compressed % alignof(int) != 0;
            same_data(rtabmap::uncompressData(encoded), expected);
        }
    }
    require(tested_unaligned, "fixture did not exercise an unaligned matrix trailer");
}

void rvl_truncation(bool use_mat)
{
    const std::array<unsigned short, 8> depth{0, 65535, 1, 2000, 0, 3200, 1, 65535};
    const cv::Mat expected(1, static_cast<int>(depth.size()), CV_16UC1,
        const_cast<unsigned short*>(depth.data()));
    const auto encoded = rtabmap::compressImage(expected, ".rvl");
    require(encoded.size() > 16, "missing valid RVL frame");
    // These native-order words encode the known zero/nonzero runs and zigzag
    // deltas. Keep the existing RVL format, including its final zero padding.
    const std::array<uint32_t, 5> words{
        0x13effff3u, 0xbffff3ebu, 0xe7138cd4u, 0xdfbc1cffu, 0xff300000u
    };
    require(encoded.size() == 16 + sizeof(words) &&
            std::memcmp(encoded.data() + 16, words.data(), sizeof(words)) == 0,
            "known RVL wire words changed");
    const auto decode = [use_mat](const std::vector<unsigned char>& bytes) {
        if (!use_mat) return rtabmap::uncompressImage(bytes);
        cv::Mat view(1, static_cast<int>(bytes.size()), CV_8UC1,
            const_cast<unsigned char*>(bytes.data()));
        return rtabmap::uncompressImage(view);
    };
    same_data(decode(encoded), expected);
    std::vector<unsigned char> shifted(encoded.size() + 1);
    std::copy(encoded.begin(), encoded.end(), shifted.begin() + 1);
    cv::Mat unaligned(1, static_cast<int>(encoded.size()), CV_8UC1, shifted.data() + 1);
    same_data(rtabmap::uncompressImage(unaligned), expected);
    // The original codec API also accepts byte buffers without word alignment.
    std::vector<unsigned char> payload(3 * depth.size() + 5);
    rtabmap::RvlCodec codec;
    const int payload_size = codec.CompressRVL(depth.data(), payload.data() + 1,
                                              static_cast<int>(depth.size()));
    require(payload_size == static_cast<int>(sizeof(words)) &&
            std::memcmp(payload.data() + 1, words.data(), sizeof(words)) == 0,
            "unaligned RVL output changed the wire words");
    std::array<unsigned short, 8> restored{};
    codec.DecompressRVL(payload.data() + 1, restored.data(), static_cast<int>(restored.size()));
    require(restored == depth, "unaligned trusted RVL input changed values");
    for (std::size_t size = 0; size < encoded.size(); ++size) {
        const std::vector<unsigned char> truncated(encoded.begin(), encoded.begin() + size);
        bool rejected = false;
        try {
            rejected = decode(truncated).empty();
        } catch (const cv::Exception&) {
            rejected = true;
        }
        require(rejected, "truncated RVL data was accepted");
    }
    // A malformed-input fix must preserve the complete valid codec path.
    same_data(decode(encoded), expected);
}
} // namespace

int main(int argc, char** argv)
{
    if (argc > 2) return 64;
    const std::string mode = argc == 1 ? "all" : argv[1];
    try {
        if (mode == "all") {
            for (const auto *data_mode : {"data-vector", "data-mat", "data-read"})
                data_round_trips(data_mode);
            rvl_truncation(false);
            rvl_truncation(true);
        } else if (mode == "data-vector" || mode == "data-mat" || mode == "data-read")
            data_round_trips(mode);
        else if (mode == "rvl-vector" || mode == "rvl-mat")
            rvl_truncation(mode == "rvl-mat");
        else return 64;
        std::cout << "PASS " << mode << '\n';
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "FAIL " << error.what() << '\n';
        return 1;
    }
}
