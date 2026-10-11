/* SPDX-License-Identifier: BSD-2-Clause
 * Origin: EmberBSD; AI-assisted EGL/GLES render and lifecycle diagnostic.
 * This tests pixels from the selected renderer, not package integration.
 */
#include <sys/types.h>

#ifdef EMBER_EPOXY_DISPATCH
#include <epoxy/egl.h>
#include <epoxy/gl.h>
#include <link_elf.h>
#else
#include <EGL/egl.h>
#include <EGL/eglext.h>
#include <GLES2/gl2.h>
#endif
#include <gbm.h>

#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#ifdef EMBER_EPOXY_DISPATCH
/* NetBSD's live loader inventory includes providers opened by libepoxy. */
static int
loaded_library(struct dl_phdr_info *info, size_t size, void *argument)
{
	const char *executable = argument;
	const char *name = info->dlpi_name;

	(void)size;
	if (name[0] == '\0' || strcmp(name, executable) == 0)
		return 0;
	if (strncmp(name, "/usr/pkg/", 9) != 0 &&
	    strncmp(name, "/usr/lib/", 9) != 0 &&
	    strncmp(name, "/lib/", 5) != 0 &&
	    strcmp(name, "/libexec/ld.elf_so") != 0 &&
	    strcmp(name, "/usr/libexec/ld.elf_so") != 0) {
		fprintf(stderr, "FAIL: unexpected loaded library: %s\n", name);
		return 1;
	}
	printf("LOADED: %s\n", name);
	return 0;
}
#endif

static void
fail(const char *message)
{

	fprintf(stderr, "FAIL: %s (EGL %#x, GL %#x)\n", message,
	    eglGetError(), glGetError());
	exit(1);
}

static GLuint
shader(GLenum kind, const char *source, int expected)
{
	GLuint object = glCreateShader(kind);
	GLint status;
	char log[512];

	if (object == 0)
		fail("glCreateShader");
	glShaderSource(object, 1, &source, NULL);
	glCompileShader(object);
	glGetShaderiv(object, GL_COMPILE_STATUS, &status);
	if ((status == GL_TRUE) != expected) {
		glGetShaderInfoLog(object, sizeof(log), NULL, log);
		fprintf(stderr, "Shader log: %s\n", log);
		fail("shader compilation status");
	}
	return object;
}

static void
expect_pixel(GLint x, GLint y, int red, int green)
{
	unsigned char pixel[4];

	glReadPixels(x, y, 1, 1, GL_RGBA, GL_UNSIGNED_BYTE, pixel);
	if (glGetError() != GL_NO_ERROR)
		fail("glReadPixels");
	if (pixel[0] != red || pixel[1] != green || pixel[2] != 0 ||
	    pixel[3] != 255) {
		fprintf(stderr, "Pixel %d,%d = %u,%u,%u,%u; expected %d,%d,0,255\n",
		    x, y, pixel[0], pixel[1], pixel[2], pixel[3], red, green);
		fail("pixel mismatch");
	}
}

static void
draw(GLsizei width, GLsizei height)
{
	static const GLfloat vertices[] = { -1, -1, 1, -1, 0, 1 };
	GLuint texture, framebuffer, vertex, fragment, invalid, program, buffer;
	GLint linked;

	invalid = shader(GL_FRAGMENT_SHADER, "this is not valid GLSL", 0);
	glDeleteShader(invalid);
	vertex = shader(GL_VERTEX_SHADER,
	    "attribute vec2 position; void main() {"
	    "gl_Position = vec4(position, 0.0, 1.0); }", 1);
	fragment = shader(GL_FRAGMENT_SHADER,
	    "precision mediump float; void main() {"
	    "gl_FragColor = vec4(0.0, 1.0, 0.0, 1.0); }", 1);
	program = glCreateProgram();
	glAttachShader(program, vertex);
	glAttachShader(program, fragment);
	glBindAttribLocation(program, 0, "position");
	glLinkProgram(program);
	glGetProgramiv(program, GL_LINK_STATUS, &linked);
	if (linked != GL_TRUE)
		fail("program link");
	glUseProgram(program);
	glGenTextures(1, &texture);
	glBindTexture(GL_TEXTURE_2D, texture);
	glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, width, height, 0, GL_RGBA,
	    GL_UNSIGNED_BYTE, NULL);
	glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST);
	glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST);
	glGenFramebuffers(1, &framebuffer);
	glBindFramebuffer(GL_FRAMEBUFFER, framebuffer);
	glFramebufferTexture2D(GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0,
	    GL_TEXTURE_2D, texture, 0);
	if (glCheckFramebufferStatus(GL_FRAMEBUFFER) != GL_FRAMEBUFFER_COMPLETE)
		fail("framebuffer completeness");
	glViewport(0, 0, width, height);
	glClearColor(1, 0, 0, 1);
	glClear(GL_COLOR_BUFFER_BIT);
	expect_pixel(width / 2, height / 2, 255, 0);
	glGenBuffers(1, &buffer);
	glBindBuffer(GL_ARRAY_BUFFER, buffer);
	glBufferData(GL_ARRAY_BUFFER, sizeof(vertices), vertices, GL_STATIC_DRAW);
	glEnableVertexAttribArray(0);
	glVertexAttribPointer(0, 2, GL_FLOAT, GL_FALSE, 0, NULL);
	glDrawArrays(GL_TRIANGLES, 0, 3);
	glFinish();
	if (glGetError() != GL_NO_ERROR)
		fail("draw and finish");
	expect_pixel(width / 2, height / 2, 0, 255);
	expect_pixel(0, height - 1, 255, 0);
	glDeleteBuffers(1, &buffer);
	glDeleteFramebuffers(1, &framebuffer);
	glDeleteTextures(1, &texture);
	glDeleteProgram(program);
	glDeleteShader(vertex);
	glDeleteShader(fragment);
	if (glGetError() != GL_NO_ERROR)
		fail("object cleanup");
}

int
main(int argc, char **argv)
{
	const EGLint config_attributes[] = {
		EGL_SURFACE_TYPE, 0, EGL_RENDERABLE_TYPE, EGL_OPENGL_ES2_BIT,
		EGL_RED_SIZE, 8, EGL_GREEN_SIZE, 8, EGL_BLUE_SIZE, 8, EGL_NONE
	};
	const EGLint context_attributes[] = {
		EGL_CONTEXT_CLIENT_VERSION, 2, EGL_NONE
	};
	PFNEGLGETPLATFORMDISPLAYEXTPROC get_display;
	struct gbm_device *gbm = NULL;
	EGLDisplay display;
	EGLConfig config;
	EGLContext context;
	EGLint major, minor, count;
	const char *renderer;
	int fd = -1;
	GLsizei width = 16, height = 16;
	unsigned cycle;
#ifdef EMBER_EPOXY_DISPATCH
	int loader_status = 0;
#endif

	if (argc != 3 && argc != 5) {
		fprintf(stderr, "Usage: mesa-render surfaceless|RENDER_NODE EXPECTED_RENDERER [WIDTH HEIGHT]\n");
		return 2;
	}
	if (argc == 5) {
		long dimensions[2];
		for (unsigned i = 0; i < 2; i++) {
			char *end;
			errno = 0;
			dimensions[i] = strtol(argv[3 + i], &end, 10);
			if (errno != 0 || *end != '\0' || end == argv[3 + i] ||
			    dimensions[i] < 16 || dimensions[i] > 4096) {
				fprintf(stderr, "Dimensions must be integers from 16 to 4096\n");
				return 2;
			}
		}
		width = (GLsizei)dimensions[0];
		height = (GLsizei)dimensions[1];
	}
	get_display = (PFNEGLGETPLATFORMDISPLAYEXTPROC)
	    eglGetProcAddress("eglGetPlatformDisplayEXT");
	if (get_display == NULL)
		fail("eglGetPlatformDisplayEXT");
	if (strcmp(argv[1], "surfaceless") != 0) {
		fd = open(argv[1], O_RDWR | O_CLOEXEC);
		if (fd < 0) {
			perror(argv[1]);
			return 1;
		}
		gbm = gbm_create_device(fd);
		if (gbm == NULL)
			fail("gbm_create_device");
	}
	for (cycle = 0; cycle < 4; cycle++) {
		display = get_display(gbm != NULL ? EGL_PLATFORM_GBM_KHR :
		    EGL_PLATFORM_SURFACELESS_MESA, gbm, NULL);
		if (display == EGL_NO_DISPLAY ||
		    !eglInitialize(display, &major, &minor))
			fail("eglInitialize");
		if (!eglBindAPI(EGL_OPENGL_ES_API) ||
		    !eglChooseConfig(display, config_attributes, &config, 1, &count) ||
		    count != 1)
			fail("EGL config");
		context = eglCreateContext(display, config, EGL_NO_CONTEXT,
		    context_attributes);
		if (context == EGL_NO_CONTEXT ||
		    !eglMakeCurrent(display, EGL_NO_SURFACE, EGL_NO_SURFACE, context))
			fail("EGL context");
		renderer = (const char *)glGetString(GL_RENDERER);
		if (renderer == NULL || strstr(renderer, argv[2]) == NULL) {
			fprintf(stderr, "Renderer: %s; required substring: %s\n",
			    renderer != NULL ? renderer : "(null)", argv[2]);
			fail("unexpected renderer");
		}
		printf("Cycle %u: EGL %d.%d; GL %s; renderer %s\n", cycle + 1,
		    major, minor, glGetString(GL_VERSION), renderer);
		printf("Render target: %dx%d\n", width, height);
		draw(width, height);
#ifdef EMBER_EPOXY_DISPATCH
		if (cycle == 0)
			loader_status = dl_iterate_phdr(loaded_library, argv[0]);
#endif
		if (!eglMakeCurrent(display, EGL_NO_SURFACE, EGL_NO_SURFACE,
		    EGL_NO_CONTEXT) || !eglDestroyContext(display, context) ||
		    !eglTerminate(display) || !eglReleaseThread())
			fail("EGL cleanup");
#ifdef EMBER_EPOXY_DISPATCH
		/* Leave the loader callback and release the context before exit. */
		if (loader_status != 0)
			return 1;
#endif
	}
	if (gbm != NULL)
		gbm_device_destroy(gbm);
	if (fd >= 0)
		close(fd);
	puts("PASS: shader rejection, clear, triangle pixels and four EGL lifecycles");
	return 0;
}
