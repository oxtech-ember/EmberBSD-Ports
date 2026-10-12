// SPDX-License-Identifier: MIT
#include <rtabmap/core/Rtabmap.h>
#include <rtabmap/core/Memory.h>
#include <rtabmap/core/VWDictionary.h>
#include <rtabmap/core/CameraModel.h>
#include <rtabmap/core/SensorData.h>
#include <opencv2/core.hpp>
#include <sqlite3.h>
#include <cmath>
#include <cstdint>
#include <iostream>
#include <stdexcept>
#include <string>
#include <set>
#include <vector>
#include <unistd.h>
static void require(bool ok, const char *message)
{
    if (!ok) throw std::runtime_error(message);
}
static int node_count(const std::string &file)
{
    sqlite3 *database = nullptr;
    require(sqlite3_open_v2(file.c_str(), &database, SQLITE_OPEN_READONLY, nullptr) == SQLITE_OK,
            "open persisted SQLite map");
    sqlite3_stmt *statement = nullptr;
    require(sqlite3_prepare_v2(database, "SELECT count(*) FROM Node", -1, &statement, nullptr) == SQLITE_OK,
            "persisted node table");
    require(sqlite3_step(statement) == SQLITE_ROW, "node count row");
    int count = sqlite3_column_int(statement, 0);
    sqlite3_finalize(statement);
    sqlite3_close(database);
    return count;
}
// Analytic RGB-D observations with explicit descriptors isolate core mapping
// from feature detection. Coordinates and matching identities are generated
// independently of RTAB-Map, PCL, registration and graph optimization.
static rtabmap::SensorData observation(int view, int id, bool unrelated = false)
{
    cv::Mat rgb(240, 320, CV_8UC3), depth(240, 320, CV_16UC1, cv::Scalar(3000));
    for (int y = 0; y < rgb.rows; ++y)
        for (int x = 0; x < rgb.cols; ++x)
            rgb.at<cv::Vec3b>(y, x) = cv::Vec3b((x + view) % 256, y % 256, (x + y) % 256);
    rtabmap::CameraModel camera(180, 180, 160, 120, rtabmap::Transform::getIdentity(), 0, rgb.size());
    rtabmap::SensorData data(rgb, depth, camera, id, 1.0 + id * 0.1);
    std::vector<cv::KeyPoint> keypoints;
    std::vector<cv::Point3f> points;
    cv::Mat descriptors(140, 32, CV_8UC1);
    for (int row = 0; row < 140; ++row) {
        const int landmark = row + view * 16;
        const float x = ((landmark % 20) - 10) * 0.12f - view * 0.1f;
        const float y = ((landmark / 20) - 6) * 0.12f;
        const float z = 3.0f + (landmark % 3) * 0.1f;
        const float u = 180 * x / z + 160, v = 180 * y / z + 120;
        points.emplace_back(x, y, z);
        keypoints.emplace_back(u, v, 8);
        depth.at<unsigned short>(int(v), int(u)) = static_cast<unsigned short>(std::lround(z * 1000));
        uint32_t random = 0x9e3779b9u ^ uint32_t(landmark + view * 1000 + (unrelated ? 50000 : 0));
        for (int column = 0; column < 32; ++column) {
            random ^= random << 13; random ^= random >> 17; random ^= random << 5;
            descriptors.at<unsigned char>(row, column) = static_cast<unsigned char>(random);
        }
    }
    data.setFeatures(keypoints, points, descriptors);
    return data;
}
int main(int argc, char **argv)
{
    try {
        require(argc == 2 && access(argv[1], F_OK) != 0, "new database path required");
        cv::setNumThreads(1);
        cv::setRNGSeed(1);
        const std::string file = argv[1];
        rtabmap::ParametersMap parameters = {
            {"Mem/IncrementalMemory", "true"}, {"Mem/STMSize", "1"},
            {"Mem/RehearsalSimilarity", "1.0"}, {"Mem/NotLinkedNodesKept", "true"},
            {"RGBD/Enabled", "true"}, {"RGBD/ProximityBySpace", "false"},
            {"RGBD/LinearUpdate", "0"}, {"RGBD/AngularUpdate", "0"},
            {"Kp/DetectorStrategy", "2"}, {"Vis/FeatureType", "2"},
            {"Vis/MinInliers", "20"}, {"Reg/Strategy", "0"},
            {"Optimizer/Strategy", "2"}, {"Rtabmap/LoopThr", "0.1"}, {"Bayes/VirtualPlacePriorThr", "0.3"},
            {"Mem/ImageCompressionFormat", ".jpg"}, {"Grid/FromDepth", "false"},
            {"Rtabmap/LogToConsole", "true"}, {"Rtabmap/LogLevel", "6"}
        };
        rtabmap::Rtabmap mapper;
        mapper.init(parameters, file, false);
        for (int view = 0; view < 6; ++view) {
            require(mapper.process(observation(view, view + 1),
                rtabmap::Transform(view * 0.1f, 0, 0, 0, 0, 0)), "mapping observation accepted");
        }
        require(mapper.getLocalOptimizedPoses().size() >= 5, "nontrivial pose graph");
        for (const auto &entry : mapper.getLocalOptimizedPoses()) {
            require(std::abs(entry.second.x() - (entry.first - 1) * 0.1) < 0.03,
                    "mapped positions agree with analytic world coordinates");
        }
        // In-session localization probe: switch params on the live mapper
        // (dictionary still in memory) before the persisted-map path.
        {
            rtabmap::ParametersMap live = parameters;
            live["Mem/IncrementalMemory"] = "false";
            live["Mem/LocalizationReadOnly"] = "false";
            mapper.parseParameters(live);
            mapper.process(observation(2, 30), rtabmap::Transform(0.45f, 0, 0, 0, 0, 0));
            {
                const rtabmap::Signature *s3 = mapper.getMemory()->getSignature(3);
                std::set<int> w3;
                if (s3) for (const auto &w : s3->getWords()) w3.insert(w.first);
                for (const auto &entry : mapper.getMemory()->getWorkingMem()) {
                    int id = entry.first;
                    const rtabmap::Signature *s = mapper.getMemory()->getSignature(id);
                    if (!s) continue;
                    int shared = 0;
                    for (const auto &w : s->getWords()) if (w3.count(w.first)) shared++;
                    std::cerr << "DBG live sig" << id << " words=" << s->getWords().size()
                              << " sharedWith3=" << shared << '\n';
                }
            }
            std::cerr << "DBG live loopClosureId=" << mapper.getLoopClosureId()
                      << " highest=" << mapper.getHighestHypothesisId()
                      << " value=" << mapper.getHighestHypothesisValue() << '\n';
        }
        mapper.close(true);
        const int count = node_count(file);
        require(count >= 5, "pose graph persisted to SQLite");
        parameters["Mem/IncrementalMemory"] = "false";
        parameters["Mem/InitWMWithAllNodes"] = "true";
        parameters["Mem/LocalizationReadOnly"] = "true";
        rtabmap::Rtabmap localizer;
        localizer.init(parameters, file, false);
        {
            // Quantize view-2 descriptors against the reopened dictionary.
            rtabmap::SensorData probe = observation(2, 25);
            std::vector<int> nn = localizer.getMemory()->getVWDictionary()->findNN(probe.descriptors());
            int matched = 0, in3 = 0;
            std::set<int> w3;
            for (const auto &w : localizer.getMemory()->getSignature(3)->getWords()) w3.insert(w.first);
            for (int id : nn) { if (id > 0) matched++; if (id > 0 && w3.count(id)) in3++; }
            std::cerr << "DBG quantize: descriptors=" << nn.size() << " matched=" << matched
                      << " inNode3=" << in3 << '\n';
        }
        auto stored = localizer.getMemory()->getNodeData(3, true, false, false, false);
        stored.uncompressData();
        require(!stored.imageRaw().empty() && stored.depthRaw().type() == CV_16UC1,
                "reopened map decodes RGB JPEG and depth PNG");
        require(stored.depthRaw().at<unsigned short>(0, 0) == 3000, "persisted metric depth");
        require(localizer.process(observation(2, 20), rtabmap::Transform(0.45f, 0, 0, 0, 0, 0)),
                "localization observation accepted");
        {
            std::cerr << "DBG loopClosureId=" << localizer.getLoopClosureId()
                      << " highest=" << localizer.getHighestHypothesisId()
                      << " value=" << localizer.getHighestHypothesisValue() << '\n';
            const rtabmap::Memory *mem = localizer.getMemory();
            std::cerr << "DBG mem WM=" << mem->getWorkingMem().size()
                      << " STM=" << mem->getStMem().size() << '\n';
            {
                const rtabmap::VWDictionary *vwb = localizer.getMemory()->getVWDictionary();
                std::cerr << "DBG dict unused=" << vwb->getUnusedWordsSize() << '\n';
            }
            for (int id : {3, 20}) {
                const rtabmap::Signature *sig = localizer.getMemory()->getSignature(id);
                if (sig) {
                    std::set<int> wids;
                    for (const auto &w : sig->getWords()) wids.insert(w.first);
                    std::cerr << "DBG sig" << id << " words=" << sig->getWords().size()
                              << " uniq=" << wids.size() << " min=" << (wids.empty()?-1:*wids.begin())
                              << " max=" << (wids.empty()?-1:*wids.rbegin()) << '\n';
                } else {
                    std::cerr << "DBG sig" << id << " absent\n";
                }
            }
            const rtabmap::Statistics &st = localizer.getStatistics();
            std::cerr << "DBG posterior:";
            for (const auto &p : st.posterior()) std::cerr << " " << p.first << ":" << p.second;
            std::cerr << "\nDBG likelihood:";
            for (const auto &p : st.likelihood()) std::cerr << " " << p.first << ":" << p.second;
            std::cerr << '\n';
        }
        require(localizer.getLoopClosureId() > 0, "known map place recognized");
        const auto pose = localizer.getLastLocalizationPose();
        require(!pose.isNull() && std::abs(pose.x() - 0.2) < 0.03 &&
                std::abs(pose.y()) < 0.03 && std::abs(pose.z()) < 0.03,
                "visual localization corrects 25 cm odometry error");
        require(!localizer.process(rtabmap::SensorData(), rtabmap::Transform::getIdentity()),
                "empty observation rejected");
        localizer.close(false);
        require(node_count(file) == count, "localization does not add map nodes");
        std::cout << "PASS persisted map/localization: nodes=" << count << " corrected_x=" << pose.x() << '\n';
        return 0;
    } catch (const std::exception &error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
