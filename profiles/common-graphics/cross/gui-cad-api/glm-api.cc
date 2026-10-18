/* SPDX-License-Identifier: BSD-2-Clause
 * Origin: EmberBSD; AI-assisted GLM installed CMake consumer.
 */
#include "loaded.h"
#include <glm/glm.hpp>
#include <glm/gtc/matrix_transform.hpp>
#include <glm/gtc/quaternion.hpp>
#include <cmath>

static bool
close(double actual, double expected)
{
	return std::isfinite(actual) && std::abs(actual - expected) < 1e-12;
}

int
main(int argc, char **argv)
{
	const double pi = std::acos(-1.0);
	const glm::dvec4 input(1, 2, 3, 1);
	const glm::dmat4 matrix =
	    glm::translate(glm::dmat4(1), glm::dvec3(2, 3, 4)) *
	    glm::rotate(glm::dmat4(1), pi / 2, glm::dvec3(0, 0, 1)) *
	    glm::scale(glm::dmat4(1), glm::dvec3(2, 3, 4));
	const glm::dvec4 mapped = matrix * input;
	const glm::dvec4 inverse = glm::inverse(matrix) * mapped;
	const glm::dquat rotation = glm::angleAxis(pi / 2, glm::dvec3(0, 0, 1));
	const glm::dvec3 rotated = rotation * glm::dvec3(1, 0, 0);

	(void)argc;
	if (!close(mapped.x, -4) || !close(mapped.y, 5) ||
	    !close(mapped.z, 16) || !close(mapped.w, 1) ||
	    !close(inverse.x, 1) || !close(inverse.y, 2) ||
	    !close(inverse.z, 3) || !close(inverse.w, 1) ||
	    !close(glm::determinant(matrix), 24) ||
	    !close(rotated.x, 0) || !close(rotated.y, 1) ||
	    !close(rotated.z, 0)) {
		fputs("FAIL: GLM matrix, inverse or quaternion values\n", stderr);
		return 1;
	}
	check_loaded(argv[0]);
	puts("PASS: GLM CMake target, affine transform, inverse, determinant and quaternion");
	return 0;
}
