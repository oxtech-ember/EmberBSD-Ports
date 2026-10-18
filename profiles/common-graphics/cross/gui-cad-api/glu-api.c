/* SPDX-License-Identifier: BSD-2-Clause
 * Origin: EmberBSD; AI-assisted GLU geometry API checks.
 */
#include "loaded.h"
#include <GL/glu.h>
#include <math.h>

struct tessellation {
	GLenum mode;
	const GLdouble *vertices[32];
	size_t count;
	unsigned int triangles;
	double area;
	int error;
};

static void
begin(GLenum mode, void *data)
{
	struct tessellation *result = data;

	result->mode = mode;
	result->count = 0;
}

static void
vertex(void *point, void *data)
{
	struct tessellation *result = data;

	if (result->count == 32) {
		result->error = 1;
		return;
	}
	result->vertices[result->count++] = point;
}

static void
triangle(struct tessellation *result, size_t a, size_t b, size_t c)
{
	const GLdouble *p = result->vertices[a];
	const GLdouble *q = result->vertices[b];
	const GLdouble *r = result->vertices[c];

	result->area += fabs((q[0] - p[0]) * (r[1] - p[1]) -
	    (q[1] - p[1]) * (r[0] - p[0])) / 2;
	result->triangles++;
}

static void
end(void *data)
{
	struct tessellation *result = data;
	size_t i;

	if (result->mode == GL_TRIANGLES && result->count % 3 == 0) {
		for (i = 0; i < result->count; i += 3)
			triangle(result, i, i + 1, i + 2);
	} else if (result->mode == GL_TRIANGLE_FAN) {
		for (i = 2; i < result->count; i++)
			triangle(result, 0, i - 1, i);
	} else if (result->mode == GL_TRIANGLE_STRIP) {
		for (i = 2; i < result->count; i++)
			triangle(result, i - 2, i - 1, i);
	} else {
		result->error = 1;
	}
}

static void
error(GLenum code, void *data)
{
	struct tessellation *result = data;

	fprintf(stderr, "GLU tessellator: %s\n", gluErrorString(code));
	result->error = 1;
}

int
main(int argc, char **argv)
{
	GLdouble polygon[6][3] = {
		{ 0, 0, 0 }, { 3, 0, 0 }, { 3, 1, 0 },
		{ 1, 1, 0 }, { 1, 3, 0 }, { 0, 3, 0 }
	};
	const GLdouble identity[16] = {
		1, 0, 0, 0, 0, 1, 0, 0,
		0, 0, 1, 0, 0, 0, 0, 1
	};
	const GLdouble singular[16] = { 0 };
	const GLint viewport[4] = { 10, 20, 200, 100 };
	struct tessellation result = { 0 };
	GLdouble x, y, z, a, b, c;
	GLUtesselator *tess;
	size_t i;

	(void)argc;
	tess = gluNewTess();
	if (tess == NULL)
		return 1;
	gluTessCallback(tess, GLU_TESS_BEGIN_DATA, (_GLUfuncptr)begin);
	gluTessCallback(tess, GLU_TESS_VERTEX_DATA, (_GLUfuncptr)vertex);
	gluTessCallback(tess, GLU_TESS_END_DATA, (_GLUfuncptr)end);
	gluTessCallback(tess, GLU_TESS_ERROR_DATA, (_GLUfuncptr)error);
	gluTessNormal(tess, 0, 0, 1);
	gluTessBeginPolygon(tess, &result);
	gluTessBeginContour(tess);
	for (i = 0; i < 6; i++)
		gluTessVertex(tess, polygon[i], polygon[i]);
	gluTessEndContour(tess);
	gluTessEndPolygon(tess);
	gluDeleteTess(tess);
	if (result.error || result.triangles != 4 ||
	    fabs(result.area - 5) > 1e-12) {
		fprintf(stderr, "FAIL: L polygon area %.17g, %u triangles\n",
		    result.area, result.triangles);
		return 1;
	}
	if (!gluProject(0.25, -0.5, 0.5, identity, identity, viewport,
	    &x, &y, &z) || fabs(x - 135) > 1e-12 ||
	    fabs(y - 45) > 1e-12 || fabs(z - 0.75) > 1e-12 ||
	    !gluUnProject(x, y, z, identity, identity, viewport, &a, &b, &c) ||
	    fabs(a - 0.25) > 1e-12 || fabs(b + 0.5) > 1e-12 ||
	    fabs(c - 0.5) > 1e-12 ||
	    gluUnProject(x, y, z, singular, identity, viewport, &a, &b, &c)) {
		fprintf(stderr, "FAIL: GLU projection or singular inverse\n");
		return 1;
	}
	check_loaded(argv[0]);
	puts("PASS: GLU concave tessellation area 5, projection and singular inverse");
	return 0;
}
