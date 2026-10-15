// SPDX-License-Identifier: MIT
// Origin: EmberBSD (AI-assisted). Independent Surface and Segmentation oracles.
#include <pcl/point_cloud.h>
#include <pcl/point_types.h>
#include <pcl/segmentation/sac_segmentation.h>
#include <pcl/surface/mls.h>

#include <algorithm>
#include <cmath>
#include <cstddef>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

namespace {
using Point = pcl::PointXYZRGB;
using Cloud = pcl::PointCloud<Point>;

void Require(bool valid, const char* message) {
  if (!valid) throw std::runtime_error(message);
}

Point MakePoint(float x, float y, float z) {
  Point point;
  point.x = x;
  point.y = y;
  point.z = z;
  point.r = 37;
  point.g = 89;
  point.b = 143;
  return point;
}

Cloud::Ptr Plane(int radius) {
  auto cloud = pcl::make_shared<Cloud>();
  for (int y = -radius; y <= radius; ++y) {
    for (int x = -radius; x <= radius; ++x) {
      const float px = 0.05f * x;
      const float py = 0.05f * y;
      cloud->push_back(MakePoint(px, py, 0.3f + 0.05f * px - 0.02f * py));
    }
  }
  return cloud;
}

void Surface(bool empty) {
  auto input = empty ? pcl::make_shared<Cloud>() : Plane(4);
  pcl::MovingLeastSquares<Point, pcl::PointXYZRGBNormal> surface;
  surface.setInputCloud(input);
  surface.setComputeNormals(true);
  surface.setPolynomialOrder(2);
  surface.setSearchRadius(0.16);
  pcl::PointCloud<pcl::PointXYZRGBNormal> output;
  surface.process(output);
  Require(output.size() == input->size(), "MLS output point count");
  const Eigen::Vector3f expected = Eigen::Vector3f(-0.05f, 0.02f, 1.0f).normalized();
  for (const auto& point : output) {
    Require(std::isfinite(point.x) && std::isfinite(point.y) &&
                std::isfinite(point.z), "MLS nonfinite position");
    Require(std::abs(point.z - 0.3f - 0.05f * point.x + 0.02f * point.y) < 5e-5f,
            "MLS point differs from analytic plane");
    const Eigen::Vector3f normal(point.normal_x, point.normal_y, point.normal_z);
    Require(normal.allFinite() && std::isfinite(point.curvature), "MLS nonfinite normal");
    Require(std::abs(normal.norm() - 1.0f) < 1e-4f &&
                std::abs(normal.dot(expected)) > 1.0f - 1e-4f,
            "MLS normal differs from analytic plane");
    Require(point.r == 37 && point.g == 89 && point.b == 143, "MLS lost point color");
  }
}

void Segmentation(bool empty) {
  auto input = empty ? pcl::make_shared<Cloud>() : Plane(3);
  const std::size_t plane_count = input->size();
  if (!empty) {
    input->push_back(MakePoint(-0.1f, 0.1f, 0.8f));
    input->push_back(MakePoint(0.2f, -0.1f, -0.5f));
    input->push_back(MakePoint(0.0f, 0.0f, 1.2f));
  }
  pcl::SACSegmentation<Point> segmentation(false);
  segmentation.setOptimizeCoefficients(true);
  segmentation.setModelType(pcl::SACMODEL_PLANE);
  segmentation.setMethodType(pcl::SAC_RANSAC);
  segmentation.setMaxIterations(100);
  segmentation.setDistanceThreshold(0.002);
  segmentation.setInputCloud(input);
  pcl::PointIndices inliers;
  pcl::ModelCoefficients coefficients;
  segmentation.segment(inliers, coefficients);
  if (empty) {
    Require(inliers.indices.empty() && coefficients.values.empty(),
            "Empty segmentation returned a model");
    return;
  }
  Require(inliers.indices.size() == plane_count, "Plane inlier count");
  std::vector<bool> seen(plane_count, false);
  for (const auto index : inliers.indices) {
    Require(index >= 0 && static_cast<std::size_t>(index) < plane_count,
            "Plane segmentation accepted an outlier");
    Require(!seen[static_cast<std::size_t>(index)], "Duplicate plane inlier");
    seen[static_cast<std::size_t>(index)] = true;
  }
  Require(std::all_of(seen.begin(), seen.end(), [](bool value) { return value; }),
          "Plane segmentation missed an analytic point");
  Require(coefficients.values.size() == 4, "Plane coefficient count");
  for (const auto value : coefficients.values) Require(std::isfinite(value), "Nonfinite plane coefficient");
  const Eigen::Vector3f normal(coefficients.values[0], coefficients.values[1], coefficients.values[2]);
  const Eigen::Vector3f expected(-0.05f, 0.02f, 1.0f);
  const float scale = normal.norm();
  Require(std::isfinite(scale) && scale > 0.0f, "Invalid plane normal");
  const float sign = normal.dot(expected) < 0.0f ? -1.0f : 1.0f;
  Require((sign * normal / scale - expected.normalized()).norm() < 1e-4f &&
              std::abs(sign * coefficients.values[3] / scale + 0.3f / expected.norm()) < 1e-4f,
          "Plane coefficients differ from independent equation");
}
}  // namespace

int main(int argc, char** argv) {
  try {
    Require(argc == 2, "Expected surface, segmentation or empty");
    const std::string mode = argv[1];
    if (mode == "surface") Surface(false);
    else if (mode == "segmentation") Segmentation(false);
    else if (mode == "empty") { Surface(true); Segmentation(true); }
    else throw std::runtime_error("Unknown expanded PCL case");
    std::cout << "PASS expanded PCL " << mode << '\n';
    return 0;
  } catch (const std::exception& error) {
    std::cerr << error.what() << '\n';
    return 1;
  }
}
