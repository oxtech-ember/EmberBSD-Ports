/* SPDX-License-Identifier: BSD-2-Clause
 * Origin: EmberBSD (AI-assisted). Real GBM/PRIME/EGL/GLES buffer preflight.
 * The red-clear/green-triangle oracle follows mesa-render.c in this directory.
 */
#include <sys/types.h>
#include <sys/stat.h>

#include <EGL/egl.h>
#include <EGL/eglext.h>
#include <GLES2/gl2.h>
#include <GLES2/gl2ext.h>
#include <gbm.h>
#include <libdrm/drm_fourcc.h>

#include <fcntl.h>
#include <inttypes.h>
#include <limits.h>
#include <link_elf.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#define SIDE 16
#define REQUIRE(test, message) do { \
	if (!(test)) { failure = (message); goto done; } \
} while (0)

/* Include providers opened dynamically by GBM and the Mesa driver loader. */
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

static bool
has_extension(const char *list, const char *name)
{
	size_t len = strlen(name);
	const char *found;

	if (list == NULL)
		return false;
	while ((found = strstr(list, name)) != NULL) {
		if ((found == list || found[-1] == ' ') &&
		    (found[len] == '\0' || found[len] == ' '))
			return true;
		list = found + len;
	}
	return false;
}

static GLuint
compile_shader(GLenum type, const char *text)
{
	GLuint object = glCreateShader(type);
	GLint compiled = GL_FALSE;
	char log[512];

	if (object == 0)
		return 0;
	glShaderSource(object, 1, &text, NULL);
	glCompileShader(object);
	glGetShaderiv(object, GL_COMPILE_STATUS, &compiled);
	if (compiled != GL_TRUE) {
		glGetShaderInfoLog(object, sizeof(log), NULL, log);
		fprintf(stderr, "Shader compile failed: %s\n", log);
		glDeleteShader(object);
		return 0;
	}
	return object;
}

static bool
cycle(const char *node, unsigned number, const char *executable, const char *expected)
{
	static const GLfloat vertices[] = { -1, -1, 1, -1, 0, 1 };
	const EGLint context_attrs[] = { EGL_CONTEXT_CLIENT_VERSION, 2, EGL_NONE };
	PFNEGLGETPLATFORMDISPLAYEXTPROC get_display;
	PFNEGLCREATEIMAGEKHRPROC create_image;
	PFNEGLDESTROYIMAGEKHRPROC destroy_image = NULL;
	PFNGLEGLIMAGETARGETRENDERBUFFERSTORAGEOESPROC image_storage;
	struct gbm_device *gbm = NULL;
	struct gbm_bo *bo = NULL;
	struct stat st;
	EGLDisplay display = EGL_NO_DISPLAY;
	EGLContext context = EGL_NO_CONTEXT;
	EGLImageKHR image = EGL_NO_IMAGE_KHR;
	EGLint major, minor;
	GLuint rb = 0, fb = 0, vertex = 0, fragment = 0, program = 0, buffer = 0;
	GLint linked = GL_FALSE;
	unsigned char pixels[SIDE * SIDE * 4];
	uint32_t stride = 0, offset = 0, map_stride = 0;
	uint64_t modifier;
	void *mapping = NULL, *map_data = NULL;
	const char *extensions, *renderer, *failure = NULL;
	bool initialized = false, current = false;
	int fd = -1, prime_fd = -1;
	unsigned x, y;

	fd = open(node, O_RDWR | O_CLOEXEC);
	REQUIRE(fd >= 0, "open real DRM device");
	REQUIRE(fstat(fd, &st) == 0 && S_ISCHR(st.st_mode), "DRM path is not a character device");
	gbm = gbm_create_device(fd);
	REQUIRE(gbm != NULL, "gbm_create_device");
	get_display = (PFNEGLGETPLATFORMDISPLAYEXTPROC)eglGetProcAddress("eglGetPlatformDisplayEXT");
	create_image = (PFNEGLCREATEIMAGEKHRPROC)eglGetProcAddress("eglCreateImageKHR");
	destroy_image = (PFNEGLDESTROYIMAGEKHRPROC)eglGetProcAddress("eglDestroyImageKHR");
	image_storage = (PFNGLEGLIMAGETARGETRENDERBUFFERSTORAGEOESPROC)
	    eglGetProcAddress("glEGLImageTargetRenderbufferStorageOES");
	REQUIRE(get_display && create_image && destroy_image && image_storage, "required EGL/GLES entrypoints");
	display = get_display(EGL_PLATFORM_GBM_KHR, gbm, NULL);
	REQUIRE(display != EGL_NO_DISPLAY && eglInitialize(display, &major, &minor), "initialize GBM EGL display");
	initialized = true;
	extensions = eglQueryString(display, EGL_EXTENSIONS);
	printf("Cycle %u: EGL %d.%d; extensions: %s\n", number, major, minor,
	    extensions != NULL ? extensions : "(null)");
	REQUIRE(has_extension(extensions, "EGL_EXT_image_dma_buf_import"), "EGL_EXT_image_dma_buf_import missing");
	REQUIRE(has_extension(extensions, "EGL_EXT_image_dma_buf_import_modifiers"), "EGL_EXT_image_dma_buf_import_modifiers missing");
	REQUIRE(has_extension(extensions, "EGL_KHR_surfaceless_context") &&
	    has_extension(extensions, "EGL_KHR_no_config_context"), "surfaceless/no-config context missing");
	REQUIRE(eglBindAPI(EGL_OPENGL_ES_API), "bind GLES API");
	context = eglCreateContext(display, EGL_NO_CONFIG_KHR, EGL_NO_CONTEXT, context_attrs);
	REQUIRE(context != EGL_NO_CONTEXT && eglMakeCurrent(display, EGL_NO_SURFACE,
	    EGL_NO_SURFACE, context), "make GLES context current");
	current = true;
	renderer = (const char *)glGetString(GL_RENDERER);
	REQUIRE(renderer != NULL && strstr(renderer, expected) != NULL, "unexpected renderer");
	printf("Renderer: %s; GBM backend: %s\n", renderer, gbm_device_get_backend_name(gbm));
	REQUIRE(has_extension((const char *)glGetString(GL_EXTENSIONS), "GL_OES_EGL_image"), "GL_OES_EGL_image missing");
	bo = gbm_bo_create(gbm, SIDE, SIDE, GBM_FORMAT_ARGB8888,
	    GBM_BO_USE_RENDERING | GBM_BO_USE_LINEAR);
	REQUIRE(bo != NULL, "allocate real linear ARGB8888 GBM BO");
	modifier = gbm_bo_get_modifier(bo);
	stride = gbm_bo_get_stride_for_plane(bo, 0);
	offset = gbm_bo_get_offset(bo, 0);
	REQUIRE(gbm_bo_get_plane_count(bo) == 1 && modifier == DRM_FORMAT_MOD_LINEAR &&
	    stride >= SIDE * 4 && stride <= INT_MAX && offset <= INT_MAX,
	    "BO must have one plane, exact LINEAR modifier and bounded stride/offset");
	prime_fd = gbm_bo_get_fd(bo);
	REQUIRE(prime_fd >= 0, "export real GBM BO as PRIME fd");
	printf("BO: format=%#x modifier=%#" PRIx64 " stride=%" PRIu32 " offset=%" PRIu32 "\n",
	    GBM_FORMAT_ARGB8888, modifier, stride, offset);
	const EGLint attrs[] = {
		EGL_WIDTH, SIDE, EGL_HEIGHT, SIDE,
		EGL_LINUX_DRM_FOURCC_EXT, DRM_FORMAT_ARGB8888,
		EGL_DMA_BUF_PLANE0_FD_EXT, prime_fd,
		EGL_DMA_BUF_PLANE0_OFFSET_EXT, (EGLint)offset,
		EGL_DMA_BUF_PLANE0_PITCH_EXT, (EGLint)stride,
		EGL_DMA_BUF_PLANE0_MODIFIER_LO_EXT, (EGLint)(modifier & UINT32_MAX),
		EGL_DMA_BUF_PLANE0_MODIFIER_HI_EXT, (EGLint)(modifier >> 32), EGL_NONE
	};
	image = create_image(display, EGL_NO_CONTEXT, EGL_LINUX_DMA_BUF_EXT, NULL, attrs);
	REQUIRE(image != EGL_NO_IMAGE_KHR, "import exported DMA-BUF as EGLImage");
	/* EGLImage owns its imported reference; the original export fd is closed. */
	close(prime_fd);
	prime_fd = -1;
	glGenRenderbuffers(1, &rb);
	glBindRenderbuffer(GL_RENDERBUFFER, rb);
	image_storage(GL_RENDERBUFFER, image);
	glGenFramebuffers(1, &fb);
	glBindFramebuffer(GL_FRAMEBUFFER, fb);
	glFramebufferRenderbuffer(GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0, GL_RENDERBUFFER, rb);
	REQUIRE(glGetError() == GL_NO_ERROR &&
	    glCheckFramebufferStatus(GL_FRAMEBUFFER) == GL_FRAMEBUFFER_COMPLETE, "imported render target FBO");
	vertex = compile_shader(GL_VERTEX_SHADER, "attribute vec2 position; void main() {"
	    "gl_Position=vec4(position,0.0,1.0); }");
	fragment = compile_shader(GL_FRAGMENT_SHADER, "precision mediump float; void main() {"
	    "gl_FragColor=vec4(0.0,1.0,0.0,1.0); }");
	REQUIRE(vertex && fragment, "triangle shader compile");
	program = glCreateProgram();
	glAttachShader(program, vertex);
	glAttachShader(program, fragment);
	glBindAttribLocation(program, 0, "position");
	glLinkProgram(program);
	glGetProgramiv(program, GL_LINK_STATUS, &linked);
	REQUIRE(linked == GL_TRUE, "triangle shader link");
	glUseProgram(program);
	glViewport(0, 0, SIDE, SIDE);
	glClearColor(1, 0, 0, 1);
	glClear(GL_COLOR_BUFFER_BIT);
	glGenBuffers(1, &buffer);
	glBindBuffer(GL_ARRAY_BUFFER, buffer);
	glBufferData(GL_ARRAY_BUFFER, sizeof(vertices), vertices, GL_STATIC_DRAW);
	glEnableVertexAttribArray(0);
	glVertexAttribPointer(0, 2, GL_FLOAT, GL_FALSE, 0, NULL);
	glDrawArrays(GL_TRIANGLES, 0, 3);
	glFinish();
	glReadPixels(0, 0, SIDE, SIDE, GL_RGBA, GL_UNSIGNED_BYTE, pixels);
	REQUIRE(glGetError() == GL_NO_ERROR, "DMA-BUF triangle and GLES readback");
	REQUIRE(memcmp(pixels + (8 * SIDE + 8) * 4, "\0\377\0\377", 4) == 0 &&
	    memcmp(pixels + (15 * SIDE) * 4, "\377\0\0\377", 4) == 0,
	    "GLES readback must show the green triangle and red background");
	mapping = gbm_bo_map(bo, 0, 0, SIDE, SIDE, GBM_BO_TRANSFER_READ, &map_stride, &map_data);
	REQUIRE(mapping != NULL && map_stride >= SIDE * 4, "map original GBM BO after glFinish");
	for (y = 0; y < SIDE; y++) {
		for (x = 0; x < SIDE; x++) {
			const unsigned char *p = pixels + (y * SIDE + x) * 4;
			uint32_t actual, expected = (uint32_t)p[3] << 24 |
			    (uint32_t)p[0] << 16 | (uint32_t)p[1] << 8 | p[2];
			memcpy(&actual, (unsigned char *)mapping + y * map_stride + x * 4, sizeof(actual));
			if (actual != expected) {
				fprintf(stderr, "CPU pixel %u,%u=%#x GLES=%#x\n", x, y, actual, expected);
				failure = "CPU mapping must match all 256 imported-render-target pixels";
				goto done;
			}
		}
	}
	/* Keep the GBM backend, EGL driver and imported BO alive for inventory. */
	REQUIRE(dl_iterate_phdr(loaded_library, (void *)executable) == 0,
	    "live loader inventory");
done:
	if (failure != NULL)
		fprintf(stderr, "FAIL cycle %u: %s (EGL=%#x)\n", number, failure, eglGetError());
	if (mapping != NULL)
		gbm_bo_unmap(bo, map_data);
	if (current) {
		glDeleteBuffers(1, &buffer);
		glDeleteProgram(program);
		glDeleteShader(vertex);
		glDeleteShader(fragment);
		glDeleteFramebuffers(1, &fb);
		glDeleteRenderbuffers(1, &rb);
		if (glGetError() != GL_NO_ERROR)
			failure = "GL cleanup";
	}
	if (image != EGL_NO_IMAGE_KHR && !destroy_image(display, image))
		failure = "EGLImage cleanup";
	if (bo != NULL)
		gbm_bo_destroy(bo);
	if (prime_fd >= 0)
		close(prime_fd);
	if (current && !eglMakeCurrent(display, EGL_NO_SURFACE, EGL_NO_SURFACE, EGL_NO_CONTEXT))
		failure = "unbind context";
	if (context != EGL_NO_CONTEXT && !eglDestroyContext(display, context))
		failure = "destroy context";
	if (initialized && !eglTerminate(display))
		failure = "terminate display";
	if (!eglReleaseThread())
		failure = "release EGL thread";
	if (gbm != NULL)
		gbm_device_destroy(gbm);
	if (fd >= 0)
		close(fd);
	if (failure != NULL) {
		fprintf(stderr, "FAIL: %s\n", failure);
		return false;
	}
	printf("PASS cycle %u: real PRIME import, GLES triangle, 256 CPU pixels and cleanup\n", number);
	return true;
}

int
main(int argc, char **argv)
{
	const char *software = getenv("LIBGL_ALWAYS_SOFTWARE");
	const char *expected = argc == 3 ? argv[2] : "llvmpipe";
	unsigned i;

	setvbuf(stdout, NULL, _IOLBF, 0);
	if ((argc != 2 && argc != 3) || strncmp(argv[1], "/dev/dri/", 9) != 0 ||
	    strstr(argv[1], "..") != NULL ||
	    (strcmp(expected, "llvmpipe") != 0 && strcmp(expected, "V3D") != 0) ||
	    (strcmp(expected, "llvmpipe") == 0 &&
	    (software == NULL || strcmp(software, "1") != 0)) ||
	    (strcmp(expected, "V3D") == 0 && software != NULL && software[0] != '\0')) {
		fprintf(stderr, "Usage: mesa-dmabuf /dev/dri/DEVICE [V3D|llvmpipe]\n"
		    "llvmpipe requires LIBGL_ALWAYS_SOFTWARE=1; V3D forbids that override.\n");
		return 2;
	}
	printf("Expected renderer: %s; a real DRM/PRIME device is required.\n", expected);
	for (i = 1; i <= 4; i++)
		if (!cycle(argv[1], i, argv[0], expected))
			return 1;
	puts("PASS: four GBM/PRIME/EGLImage/GLES/CPU-readback lifecycles; renderer verified above");
	return 0;
}
