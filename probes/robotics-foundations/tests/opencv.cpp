// SPDX-License-Identifier: MIT
#include <Eigen/Dense>
#include <opencv2/core.hpp>
#include <opencv2/core/eigen.hpp>
#include <opencv2/imgproc.hpp>
#include <opencv2/imgcodecs.hpp>
#include <opencv2/features.hpp>
#include <opencv2/geometry.hpp>
#include <cmath>
#include <iostream>
#include <stdexcept>
#include <vector>

static void require(bool ok, const char *what)
{
    if (!ok) throw std::runtime_error(what);
}

int main()
{
    // Exercise two workers below, then join the pool before process teardown.
    // This also releases the workers' TLS when any check throws.
    struct ThreadCleanup {
        ~ThreadCleanup() { cv::setNumThreads(1); }
    } thread_cleanup;
    try {
        require(cv::getVersionString() == "5.0.0", "runtime version");
        std::cout << cv::getBuildInformation() << '\n';
#if defined(__NetBSD__) && defined(__aarch64__)
        require(cv::checkHardwareSupport(CV_CPU_NEON), "AArch64 NEON detection");
        require(cv::checkHardwareSupport(CV_CPU_FP16), "AArch64 half conversion detection");
        cv::Mat full(cv::Matx<float, 1, 4>(0.0f, 1.0f, -2.0f, 0.5f)), half, restored;
        full.convertTo(half, CV_16F);
        half.convertTo(restored, CV_32F);
        require(cv::norm(full, restored, cv::NORM_INF) == 0, "half conversion round trip");
#endif
        cv::setNumThreads(2);
        cv::setRNGSeed(7);
        cv::Mat image = cv::Mat::zeros(128, 128, CV_8UC3);
        cv::rectangle(image, cv::Rect(24, 32, 40, 30), cv::Scalar(255, 255, 255), cv::FILLED);
        std::vector<uchar> encoded;
        require(cv::imencode(".ppm", image, encoded), "PPM encode");
        cv::Mat decoded = cv::imdecode(encoded, cv::IMREAD_COLOR);
        require(decoded.size() == image.size() && decoded.type() == image.type() &&
                cv::norm(decoded, image, cv::NORM_INF) == 0, "PPM round trip");
        cv::Mat gray, mask, labels, stats, centroids;
        cv::cvtColor(decoded, gray, cv::COLOR_BGR2GRAY);
        cv::threshold(gray, mask, 127, 255, cv::THRESH_BINARY);
        require(cv::connectedComponentsWithStats(mask, labels, stats, centroids) == 2,
                "segmentation count");
        require(stats.at<int>(1, cv::CC_STAT_AREA) == 1200 &&
                std::abs(centroids.at<double>(1, 0) - 43.5) < 1e-12 &&
                std::abs(centroids.at<double>(1, 1) - 46.5) < 1e-12, "segment geometry");
        cv::Mat edges;
        cv::Canny(gray, edges, 50, 150);
        require(cv::countNonZero(edges) > 100, "edge detection");
        cv::Mat texture(256, 256, CV_8UC1);
        cv::randu(texture, 0, 256);
        std::vector<cv::KeyPoint> keypoints;
        cv::Mat descriptors;
        cv::ORB::create(200)->detectAndCompute(texture, cv::noArray(), keypoints, descriptors);
        require(keypoints.size() >= 50 && descriptors.rows == static_cast<int>(keypoints.size()),
                "ORB feature extraction");
        std::vector<cv::DMatch> matches;
        cv::BFMatcher(cv::NORM_HAMMING, true).match(descriptors, descriptors, matches);
        require(matches.size() == keypoints.size(), "feature match count");
        for (const auto &m : matches) require(m.distance == 0, "feature self match");
        std::vector<cv::Point3d> world{{0,0,0},{1,0,0},{0,1,0},{1,1,0},
                                     {0,0,1},{1,0,1},{0,1,1},{1,1,1}};
        const cv::Mat camera(cv::Matx33d(800,0,320, 0,800,240, 0,0,1));
        const cv::Vec3d rotation(0.1, -0.05, 0.02), translation(0.2, -0.1, 5);
        std::vector<cv::Point2d> pixels;
        cv::projectPoints(world, rotation, translation, camera, cv::noArray(), pixels);
        cv::Vec3d solved_r, solved_t;
        require(cv::solvePnP(world, pixels, camera, cv::noArray(), solved_r, solved_t), "pose solve");
        require(cv::norm(solved_t - translation) < 1e-6 &&
                cv::norm(solved_r - rotation) < 1e-6, "pose recovery");
        Eigen::Matrix3d eigen;
        cv::cv2eigen(camera, eigen);
        cv::Mat back;
        cv::eigen2cv(eigen, back);
        require(cv::norm(camera, back, cv::NORM_INF) == 0, "Eigen interoperation");
        require(cv::imdecode(std::vector<uchar>{1,2,3,4}, cv::IMREAD_COLOR).empty(),
                "malformed image rejected");
        bool rejected = false;
        try { cv::cvtColor(cv::Mat(), gray, cv::COLOR_BGR2GRAY); }
        catch (const cv::Exception &) { rejected = true; }
        require(rejected, "empty image rejected");
        std::cout << "PASS OpenCV 5.0.0: PPM, segmentation, edges, ORB, pose, Eigen, invalid inputs\n";
    } catch (const std::exception &e) {
        std::cerr << "FAIL OpenCV: " << e.what() << '\n';
        return 1;
    }
}
