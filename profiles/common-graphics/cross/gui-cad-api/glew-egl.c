/* SPDX-License-Identifier: BSD-2-Clause
 * Origin: EmberBSD; AI-assisted desktop OpenGL under EGL acceptance.
 */
#include "loaded.h"
#include <GL/glew.h>
#include <EGL/egl.h>
#include <EGL/eglext.h>

static void
require(int condition, const char *message)
{

	if (!condition) {
		fprintf(stderr, "FAIL: %s (EGL %#x)\n", message, eglGetError());
		exit(1);
	}
}

int
main(int argc, char **argv)
{
	const EGLint attributes[] = {
		EGL_SURFACE_TYPE, EGL_PBUFFER_BIT,
		EGL_RENDERABLE_TYPE, EGL_OPENGL_BIT,
		EGL_RED_SIZE, 8, EGL_GREEN_SIZE, 8, EGL_BLUE_SIZE, 8,
		EGL_NONE
	};
	const EGLint surface_attributes[] = { EGL_WIDTH, 8, EGL_HEIGHT, 8, EGL_NONE };
	const EGLint context_attributes[] = { EGL_NONE };
	PFNEGLGETPLATFORMDISPLAYEXTPROC platform_display;
	EGLDisplay display;
	EGLContext context;
	EGLSurface surface;
	EGLConfig config;
	EGLint count, major, minor;
	GLenum status;
	GLuint buffer;
	GLint size;
	unsigned char pixel[4];
	unsigned int iteration;

	(void)argc;
	require(glewInit() == GLEW_ERROR_NO_GL_VERSION,
	    "GLEW rejects missing GL context");
	platform_display = (PFNEGLGETPLATFORMDISPLAYEXTPROC)
	    eglGetProcAddress("eglGetPlatformDisplayEXT");
	require(platform_display != NULL, "EGL platform display extension");
	display = platform_display(EGL_PLATFORM_SURFACELESS_MESA,
	    EGL_DEFAULT_DISPLAY, NULL);
	require(display != EGL_NO_DISPLAY, "surfaceless EGL display");
	require(eglInitialize(display, &major, &minor), "EGL initialize");
	require(eglBindAPI(EGL_OPENGL_API), "desktop OpenGL API selection");
	require(eglChooseConfig(display, attributes, &config, 1, &count) &&
	    count == 1, "OpenGL pbuffer configuration");
	for (iteration = 0; iteration < 4; iteration++) {
		surface = eglCreatePbufferSurface(display, config, surface_attributes);
		require(surface != EGL_NO_SURFACE, "pbuffer creation");
		context = eglCreateContext(display, config, EGL_NO_CONTEXT,
		    context_attributes);
		require(context != EGL_NO_CONTEXT, "desktop GL context creation");
		require(eglMakeCurrent(display, surface, surface, context), "make current");
		printf("GL_VERSION: %s\nGL_RENDERER: %s\n", glGetString(GL_VERSION),
		    glGetString(GL_RENDERER));
		glewExperimental = GL_TRUE;
		status = glewInit();
		printf("GLEW_INIT: %u %s\n", status, glewGetErrorString(status));
		require(status == GLEW_OK, "GLEW initializes a valid EGL desktop context");
		require(GLEW_VERSION_2_0 && glGenBuffers != NULL,
		    "OpenGL extension dispatch");
		while (glGetError() != GL_NO_ERROR)
			continue;
		glGenBuffers(1, &buffer);
		glBindBuffer(GL_ARRAY_BUFFER, buffer);
		glBufferData(GL_ARRAY_BUFFER, 16, NULL, GL_STATIC_DRAW);
		glGetBufferParameteriv(GL_ARRAY_BUFFER, GL_BUFFER_SIZE, &size);
		require(size == 16, "GLEW dispatched buffer data");
		glDeleteBuffers(1, &buffer);
		glViewport(0, 0, 8, 8);
		glClearColor(0, 1, 0, 1);
		glClear(GL_COLOR_BUFFER_BIT);
		glReadPixels(4, 4, 1, 1, GL_RGBA, GL_UNSIGNED_BYTE, pixel);
		require(glGetError() == GL_NO_ERROR && pixel[0] == 0 &&
		    pixel[1] == 255 && pixel[2] == 0 && pixel[3] == 255,
		    "desktop GL exact pixel");
		require(eglMakeCurrent(display, EGL_NO_SURFACE, EGL_NO_SURFACE,
		    EGL_NO_CONTEXT), "release GL context");
		require(eglDestroyContext(display, context), "destroy GL context");
		require(eglDestroySurface(display, surface), "destroy pbuffer");
		require(glewInit() == GLEW_ERROR_NO_GL_VERSION,
		    "GLEW rejects released context");
	}
	require(eglTerminate(display), "EGL terminate");
	eglReleaseThread();
	check_loaded(argv[0]);
	puts("PASS: GLEW desktop EGL dispatch, exact pixels and four lifecycles");
	return 0;
}
