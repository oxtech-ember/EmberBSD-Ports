// SPDX-License-Identifier: MIT
#include <cam/CamRadtan.h>
#include <core/VioManager.h>
#include <state/State.h>
#include <utils/sensor_data.h>
#include <algorithm>
#include <cmath>
#include <iostream>
#include <memory>
#include <stdexcept>
#include <vector>

static void require(bool ok, const char *message)
{
    if (!ok) throw std::runtime_error(message);
}
// Analytic fixture, independent of the OpenVINS simulator and propagation code.
static Eigen::Vector3d position(double t)
{
    return {0.4 * std::sin(t), 0.25 * std::sin(0.7 * t), 0.15 * std::sin(0.9 * t)};
}
static Eigen::Vector3d velocity(double t)
{
    return {0.4 * std::cos(t), 0.175 * std::cos(0.7 * t), 0.135 * std::cos(0.9 * t)};
}
static Eigen::Vector3d acceleration(double t)
{
    return {-0.4 * std::sin(t), -0.1225 * std::sin(0.7 * t), -0.1215 * std::sin(0.9 * t)};
}
int main()
{
    try {
        ov_msckf::VioManagerOptions options;
        options.state_options.num_cameras = 1;
        options.state_options.max_clone_size = 8;
        options.state_options.max_slam_features = 0;
        options.state_options.max_aruco_features = 0;
        // The profile builds without ArUco support; keep the tracker off.
        options.use_aruco = false;
        // A sensor with a visible bias drift so the visual corrections have
        // an identifiable acceleration bias to estimate.
        options.imu_noises.sigma_ab = 0.02;
        options.num_opencv_threads = 1;
        options.use_multi_threading_pubs = false;
        options.use_multi_threading_subs = false;
        options.vec_dw << 1, 0, 0, 1, 0, 1;
        options.vec_da = options.vec_dw;
        options.vec_tg.setZero();
        options.q_ACCtoIMU << 0, 0, 0, 1;
        options.q_GYROtoIMU = options.q_ACCtoIMU;
        auto camera = std::make_shared<ov_core::CamRadtan>(640, 480);
        Eigen::VectorXd calibration(8);
        calibration << 300, 300, 320, 240, 0, 0, 0, 0;
        camera->set_value(calibration);
        // The camera maps are keyed by camera id; operator[] inserts.
        options.camera_intrinsics[0] = camera;
        Eigen::VectorXd extrinsic(7);
        extrinsic << 0, 0, 0, 1, 0, 0, 0;
        options.camera_extrinsics[0] = extrinsic;
        // The initializer carries its own camera calibrations and validates
        // them first; the upstream simulation runners copy the maps there.
        options.init_options.camera_intrinsics = options.camera_intrinsics;
        options.init_options.camera_extrinsics = options.camera_extrinsics;
        ov_msckf::VioManager estimator(options);
        Eigen::Matrix<double, 17, 1> initial = Eigen::Matrix<double, 17, 1>::Zero();
        initial(0) = 1.0;
        initial(4) = 1.0;
        initial.segment<3>(5) = position(0);
        initial.segment<3>(8) = velocity(0);
        estimator.initialize_with_gt(initial); // Only the initial state is supplied.
        std::vector<Eigen::Vector3d> landmarks;
        for (int y = -4; y <= 4; ++y)
            for (int x = -5; x <= 5; ++x)
                landmarks.emplace_back(x * 0.28, y * 0.24, 3.5 + 0.17 * ((x * x + y * y) % 7));
        int imu_index = 0;
        size_t accepted_features = 0;
        double max_error = 0;
        for (int frame = 1; frame <= 160; ++frame) {
            const double t = frame * 0.05;
            // Include the next IMU sample so interpolation brackets camera time.
            while (imu_index * 0.005 <= t + 0.005) {
                const double ti = imu_index++ * 0.005;
                ov_core::ImuData imu;
                imu.timestamp = 1.0 + ti;
                imu.wm.setZero();
                // Unmodelled acceleration bias makes inertial-only drift visible.
                imu.am = acceleration(ti) + Eigen::Vector3d(0.05, -0.025, 9.81);
                estimator.feed_measurement_imu(imu);
            }
            std::vector<std::vector<std::pair<size_t, Eigen::VectorXf>>> observations(1);
            for (size_t i = 0; i < landmarks.size(); ++i) {
                const Eigen::Vector3d point = landmarks[i] - position(t);
                Eigen::VectorXf pixel(2);
                pixel << float(300 * point.x() / point.z() + 320),
                         float(300 * point.y() / point.z() + 240);
                // End tracks regularly, exercising MSCKF triangulation and updates.
                const size_t id = 1000 + i + (frame / 16) * landmarks.size();
                observations[0].emplace_back(id, pixel);
            }
            estimator.feed_measurement_simulation(1.0 + t, {0}, observations);
            auto state = estimator.get_state();
            require(std::abs(state->_timestamp - (1.0 + t)) < 1e-9, "camera state timestamp");
            const double error = (state->_imu->pos() - position(t)).norm();
            require(std::isfinite(error), "finite pose");
            max_error = std::max(max_error, error);
            accepted_features += estimator.get_good_features_MSCKF().size();
        }
        auto state = estimator.get_state();
        require(accepted_features > 100, "visual features accepted by MSCKF");
        require(max_error < 0.15, "analytic trajectory position error below 15 cm");
        require((state->_imu->vel() - velocity(8)).norm() < 0.12, "analytic velocity error below 12 cm/s");
        require(state->_imu->quat().head<3>().norm() < 0.025, "orientation stays near identity");
        // The unmodelled bias magnitude stays far below the uncorrected
        // inertial drift it would cause: the visual corrections absorb it.
        // Filter convergence on the bias value itself is not asserted here.
        const double timestamp = state->_timestamp;
        const Eigen::Vector3d before = state->_imu->pos();
        estimator.feed_measurement_simulation(timestamp - 0.1, {0}, {{}});
        require(state->_timestamp == timestamp && (state->_imu->pos() - before).norm() == 0,
                "out-of-order camera measurement does not rewind the estimator");
        std::cout << "PASS analytic VIO: max_position_error=" << max_error
                  << " accepted_msckf_features=" << accepted_features << '\n';
        return 0;
    } catch (const std::exception &error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
