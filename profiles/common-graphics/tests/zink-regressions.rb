#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted). Exercise actual upstream code.
require 'digest'
require 'fileutils'
require 'json'
require 'open3'
require 'shellwords'

abort 'usage: zink-regressions.rb UPSTREAM_MESA_SOURCE HOST_CLANG NEW_WORK' unless ARGV.size == 3
source, clang = ARGV.first(2).map { |p| File.realpath(p) }
work = File.expand_path(ARGV.last)
abort 'Use a new absolute work directory' unless ARGV.last.start_with?('/') && !File.exist?(work)
owner = File.expand_path('../recipes/graphics/MesaLib', __dir__)
FileUtils.mkdir_p(work)
records = []
run = lambda do |name, argv, cwd: work, env: {}|
  text, status = Open3.capture2e(env, *argv, chdir: cwd)
  File.write("#{work}/#{name}.log", text)
  records << {name: name, argv: argv, cwd: cwd, environment: env,
              status: status.exitstatus, signal: status.termsig}
  File.write("#{work}/commands.json", JSON.pretty_generate(records) + "\n")
  [text, status]
end
paths = %w[zink_resource.c zink_query.c].map { |n| "src/gallium/drivers/zink/#{n}" }
inputs = paths.to_h { |p| [p, Digest::SHA256.file("#{source}/#{p}").hexdigest] }
%w[before after].each do |variant|
  paths.each do |path|
    target = "#{work}/#{variant}/#{path}"
    FileUtils.mkdir_p(File.dirname(target))
    FileUtils.cp("#{source}/#{path}", target)
  end
end
%w[resource query].each do |name|
  path = "#{owner}/patches/patch-src_gallium_drivers_zink_zink__#{name}.c"
  inputs[path] = Digest::SHA256.file(path).hexdigest
  _, status = run.call("patch-#{name}", ['patch', '-f', '-N', '-F', '0', '-p0', '-i', path], cwd: "#{work}/after")
  abort "Patch failed: #{name}" unless status.success?
end

# The harness supplies the adjacent APIs. The lifetime block and cleanup branch
# are copied without edits from the actual source. No GPU is required.
resource_preamble = <<~C
  #include <assert.h>
  #include <stdbool.h>
  #include <stdint.h>
  #include <stdio.h>
  #define HAVE_LIBDRM 1
  #define PIPE_BIND_SCANOUT 1
  #define DRM_FORMAT_MOD_LINEAR 0
  #define WINSYS_HANDLE_TYPE_FD 1
  struct winsys_handle { int type; uint64_t modifier; int handle; };
  struct pipe_resource { unsigned bind; };
  struct zink_screen { void *ro; struct { bool have_EXT_image_drm_format_modifier; } info; };
  struct resource { void *ro_scanout; void *obj; uint64_t modifiers[1]; unsigned modifiers_count; };
  static int token;
  static volatile int imported;
  __attribute__((noinline)) static void *
  renderonly_scanout_for_resource(struct pipe_resource *templ, void *ro,
      struct winsys_handle *handle)
  {
  	(void)templ; (void)ro;
  	*handle = (struct winsys_handle){WINSYS_HANDLE_TYPE_FD, 0, 77};
  	return &token;
  }
  __attribute__((noinline)) static void *
  resource_object_create(struct zink_screen *screen, struct pipe_resource *templ,
      struct winsys_handle *handle, bool *linear, uint64_t *modifiers,
      unsigned count, const void *loader_private, const void *user_mem)
  {
  	(void)screen; (void)templ; (void)linear; (void)modifiers;
  	(void)count; (void)loader_private; (void)user_mem;
  	imported = handle->handle;
  	return &token;
  }
  int
  main(void)
  {
  	struct zink_screen storage = {&token, {true}}, *screen = &storage;
  	struct resource object = {0}, *res = &object;
  	struct pipe_resource templ2 = {PIPE_BIND_SCANOUT};
  	struct winsys_handle *whandle = NULL;
  	int modifiers_count = 0;
  	bool linear = false;
  	const void *loader_private = NULL, *user_mem = NULL;
C
resource_postamble = <<~C
  	return res->obj && imported == 77 ? 0 : 1;
  fail:
  	return 2;
  }
C
query_preamble = <<~C
  #include <stdbool.h>
  #include <stddef.h>
  #include <stdio.h>
  #include <stdlib.h>
  #define PIPE_QUERY_DRIVER_SPECIFIC 1000
  #define PIPE_QUERY_GPU_FINISHED 1
  #define PIPE_QUERY_TIMESTAMP_DISJOINT 2
  struct pipe_query { int unused; };
  struct zink_query { unsigned index, type; int vkqtype, buffers; bool precise; };
  static int allocations;
  static void *
  tracked_alloc(size_t size)
  {
  	void *p = calloc(1, size);
  	if (p != NULL)
  		allocations++;
  	return p;
  }
  static void
  tracked_free(void *p)
  {
  	if (p != NULL)
  		allocations--;
  	free(p);
  }
  #define CALLOC_STRUCT(type) tracked_alloc(sizeof(struct type))
  #define free tracked_free
  static void list_inithead(int *head) { *head = 0; }
  static int
  convert_query_type(void *screen, unsigned query_type, bool *precise)
  {
  	(void)screen; (void)query_type; (void)precise;
  	return -1;
  }
  static struct pipe_query *
  create_query(unsigned query_type, unsigned index)
  {
  	void *screen = NULL;
C
query_postamble = <<~C
  	return (struct pipe_query *)query;
  }
  int
  main(void)
  {
  	struct pipe_query *query = create_query(3, 0);
  	if (query != NULL || allocations != 0) {
  		fprintf(stderr, "unsupported query allocation imbalance: %d\\n", allocations);
  		return 1;
  	}
  	query = create_query(PIPE_QUERY_GPU_FINISHED, 0);
  	if (query == NULL || allocations != 1)
  		return 2;
  	free(query);
  	query = create_query(PIPE_QUERY_DRIVER_SPECIFIC, 0);
  	if (query == NULL || allocations != 1)
  		return 3;
  	free(query);
  	return allocations != 0;
  }
C
%w[before after].each do |variant|
  data = File.read("#{work}/#{variant}/#{paths.first}")
  function = data.index("\nresource_create(") or abort 'Missing resource_create'
  first = data.index('#ifdef HAVE_LIBDRM', function) or abort 'Missing scanout block'
  call = data.index('   res->obj = resource_object_create(', first) or abort 'Missing resource import'
  last = data.index(';', call) or abort 'Missing resource import end'
  block = data[first..last]
  data = File.read("#{work}/#{variant}/#{paths.last}")
  first = data.index('   struct zink_query *query = CALLOC_STRUCT(zink_query);') or abort 'Missing query allocation'
  last = data.index('   query->starts =', first) or abort 'Missing query prefix end'
  prefix = data[first...last]
  {'resource' => resource_preamble + block + "\n" + resource_postamble,
   'query' => query_preamble + prefix + query_postamble}.each do |name, content|
    path = "#{work}/#{variant}-#{name}.c"
    File.write(path, content)
    inputs[path] = Digest::SHA256.file(path).hexdigest
    binary = path.delete_suffix('.c')
    _, status = run.call("#{variant}-#{name}-build", [clang, *Shellwords.split(ENV.fetch('CFLAGS', '')), '-O1', '-g', '-std=c11',
      '-Wall', '-Wextra', '-Werror', '-fsanitize=address,undefined',
      '-fsanitize-address-use-after-scope', '-fno-sanitize-recover=all', path, '-o', binary])
    abort "Build failed: #{variant}-#{name}" unless status.success?
    text, status = run.call("#{variant}-#{name}-run", [binary],
      env: {'ASAN_OPTIONS' => 'halt_on_error=1:detect_stack_use_after_return=1',
            'UBSAN_OPTIONS' => 'halt_on_error=1:print_stacktrace=1'})
    expected = name == 'resource' ? 'stack-use-after-scope' : 'unsupported query allocation imbalance: 1'
    pass = variant == 'before' ? (!status.success? && text.include?(expected)) : status.success?
    abort "Unexpected result: #{variant}-#{name}" unless pass
    puts "PASS: #{variant}-#{name} #{variant == 'before' ? 'detects upstream defect' : 'passes'}"
  end
end
File.write("#{work}/receipt.json", JSON.pretty_generate({inputs_sha256: inputs, commands: records,
  boundary: 'Actual source blocks with adjacent API models. ASan/UBSan and an allocation balance check. No GPU, target execution or Valgrind result.'}) + "\n")
