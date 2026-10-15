// SPDX-License-Identifier: MIT
// AI-assisted regression for the EmberBSD RTAB-Map port.
#include <rtabmap/core/FlannIndex.h>
#include <lz4.h>
#include <cmath>
#include <cstddef>
#include <cstring>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

static_assert(LZ4_VERSION_NUMBER == 11000, "Shared LZ4 1.10.0 headers required");

static void require(bool condition, const char *message)
{
    if (!condition) throw std::runtime_error(message);
}

static void check_neighbors(const rtabmap::FlannIndex &index, const cv::Mat &queries)
{
    cv::Mat indices, distances;
    // Unlimited checks give the exact answer from the private KD-tree backend.
    index.knnSearch(queries, indices, distances, 2, -1, 0.0f, true);
    require(indices.rows == queries.rows && indices.cols == 2,
            "nearest-neighbor index dimensions");
    require(indices.type() == (sizeof(std::size_t) == 8 ? CV_64F : CV_32S),
            "nearest-neighbor index storage");
    require(distances.rows == queries.rows && distances.cols == 2 &&
            distances.type() == CV_32F, "nearest-neighbor distance dimensions");
    for (int row = 0; row < queries.rows; ++row) {
        const std::size_t expected[2] = {
            static_cast<std::size_t>(row),
            static_cast<std::size_t>(row == queries.rows - 1 ? row - 1 : row + 1)
        };
        // Dimension zero separates rows by 4. Other dimensions vary by at
        // most 22/256. A 0.25 query offset gives the exact row as nearest and
        // its directed adjacent row as second. The latter squared distance
        // is below 14.292, while the opposite neighbor starts at 18.0625.
        int squared_sum = 0;
        for (int column = 1; column < 32; ++column) {
            const int delta = (static_cast<int>(expected[1]) * 17 + column * 13) % 23 -
                              (row * 17 + column * 13) % 23;
            squared_sum += delta * delta;
        }
        // These binary fractions and their sums are exactly representable.
        const float expected_distances[2] = {
            0.0625f, 14.0625f + squared_sum / 65536.0f
        };
        for (int column = 0; column < 2; ++column) {
            std::size_t actual = 0;
            std::memcpy(&actual, indices.ptr(row) + column * sizeof(actual), sizeof(actual));
            require(actual == expected[column], "known nearest-neighbor identity");
            const float distance = distances.at<float>(row, column);
            require(std::isfinite(distance) && distance == expected_distances[column],
                    "known squared Euclidean distance");
        }
    }
}

int main()
{
    try {
        require(LZ4_versionNumber() == 11000, "shared LZ4 runtime version before private use");
        cv::Mat features(100, 32, CV_32FC1), queries(100, 32, CV_32FC1);
        for (int row = 0; row < features.rows; ++row) {
            const float offset = row == features.rows - 1 ? -0.25f : 0.25f;
            for (int column = 0; column < features.cols; ++column) {
                features.at<float>(row, column) = column == 0 ? row * 4.0f :
                    ((row * 17 + column * 13) % 23) / 256.0f;
                queries.at<float>(row, column) = features.at<float>(row, column) +
                    (column == 0 ? offset : 0.0f);
            }
        }
        std::vector<unsigned char> saved;
        {
            rtabmap::FlannIndex original;
            original.buildIndex(rtabmap::FlannIndex::FLANN_INDEX_KDTREE, features);
            require(original.isBuilt() && original.indexedFeatures() == 100,
                    "private KD-tree build");
            check_neighbors(original, queries);
            saved = original.serializeIndex(true);
            require(saved.size() > 12 * sizeof(int), "private compressed index serialization");
        }
        {
            rtabmap::FlannIndex restored;
            std::string error;
            if (!restored.loadIndex(saved, rtabmap::FlannIndex::FLANN_INDEX_KDTREE,
                                    features, false, 2.0f, &error)) {
                throw std::runtime_error("private index reload: " + error);
            }
            require(restored.isBuilt() && restored.indexedFeatures() == 100,
                    "private KD-tree restored count");
            check_neighbors(restored, queries);
        }
        require(LZ4_versionNumber() == 11000, "shared LZ4 runtime version after private use");
        std::cout << "PASS private KD-tree 100x32: compressed save/load, nearest 2, shared LZ4 11000\n";
        return 0;
    } catch (const std::exception &error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
