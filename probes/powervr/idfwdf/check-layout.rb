#!/usr/bin/env ruby
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EmberBSD contributors. AI-assisted source regression.
require 'digest'
require 'fileutils'
require 'json'
require 'open3'
require 'shellwords'

abort 'usage: check-layout.rb MESA_SOURCE NEW_WORK' unless ARGV.size == 2
source = File.realpath(ARGV[0])
work = File.expand_path(ARGV[1])
abort 'work already exists' if File.exist?(work)
paths = %w[
  src/imagination/common/pvr_iface.h
  src/imagination/include/hwdef/rogue_hw_defs.h
  src/imagination/vulkan/pvr_common.h
  src/imagination/vulkan/pvr_arch_device.c
  src/imagination/pco/usclib/common.cl
  src/imagination/pco/usclib/libcl.h
]
text = paths.to_h { |path| [path, File.read(File.join(source, path))] }
iface, hw, common, producer, shader, libcl = paths.map { |path| text.fetch(path) }
image = common[/struct pvr_image_descriptor \{\n(   uint64_t words\[[^\n]+\n)/, 1] or abort 'image words missing'
sampler = common[/struct pvr_sampler_descriptor \{\n(   uint64_t words\[[^\n]+\n)/, 1] or abort 'sampler words missing'
counts = hw.lines.grep(/^#define ROGUE_NUM_TEXSTATE_(IMAGE|SAMPLER)_WORDS /).join
abort 'descriptor counts missing' unless counts.lines.size == 2
block = producer[/   \/\* Fill the shareds buffer\. \*\/\n(.*?)   pvr_bo_cpu_unmap\(/m, 1] or abort 'packing block missing'
abort 'unexpected packing block' unless block.scan('memcpy(').size == 2 && block.include?('PVR_IDFWDF_DATA_ADDR_HI')
shader_body = shader[/^cs_idfwdf_common\(void\)\n\{.*?^}/m] or abort 'shader missing'
abort 'shader ABI include missing' unless shader.include?('#include "libcl.h"') && libcl.include?('#include "common/pvr_iface.h"')
%w[TEX SMP].each do |field|
  abort "shader descriptor width changed: #{field}" unless shader_body.include?("nir_load_preamble(4, PVR_IDFWDF_DATA_#{field}, 0)")
end
%w[ADDR_LO ADDR_HI].each do |field|
  abort "shader address input changed: #{field}" unless shader_body.include?("nir_load_preamble(1, PVR_IDFWDF_DATA_#{field}, 0)")
end
FileUtils.mkdir_p(work)
File.write("#{work}/pvr_iface.h", iface)
File.write("#{work}/shader-source.cl", shader_body)
fixture = <<~C
/* MIT. Packing block: Imagination Technologies Ltd., Mesa 26.2.4.
 * Test transport and assertions: EmberBSD contributors, AI-assisted.
 * This exercises the original producer statements, not a Vulkan device.
 */
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <stdio.h>
#include "pvr_iface.h"
#{counts}
struct image_state { #{image} };
struct sampler_state { #{sampler} };
struct addr { uint64_t addr; };
struct vma { struct addr dev_addr; };
struct bo { void *map; };
struct buffer { struct bo *bo; struct vma *vma; };
struct device { struct { struct buffer *shareds_bo, *store_bo; } idfwdf_state; };
static unsigned int checks;
#define CHECK(c) do { checks++; if (!(c)) { fprintf(stderr, "FAIL line %u: %s\\n", (unsigned int)__LINE__, #c); exit(1); } } while (0)
static void pack(struct device *device, struct image_state image_state,
                 struct sampler_state sampler_state)
{
   uint32_t *dword_ptr;
#{block}}
int main(void)
{
   struct image_state image;
   struct sampler_state sampler;
   struct vma vma;
   struct bo bo;
   struct buffer shared = { .bo = &bo }, store = { .vma = &vma };
   struct device device = { .idfwdf_state = { &shared, &store } };
   unsigned int pass;
   size_t bytes = _PVR_IDFWDF_DATA_COUNT * sizeof(uint32_t);

   /* Allocate the exact producer size. ASan detects the original overflow. */
   bo.map = malloc(bytes);
   CHECK(bo.map != NULL);
   for (pass = 0; pass < 64; pass++) {
      uint32_t *words = bo.map;
      image.words[0] = UINT64_C(0x1234567800000000) + pass;
      image.words[1] = UINT64_C(0x9abcdef000000000) + pass;
      sampler.words[0] = UINT64_C(0x3141592700000000) + pass;
      sampler.words[1] = UINT64_C(0x2718281800000000) + pass;
      vma.dev_addr.addr = UINT64_C(0x8000000400) + pass * 4;
      memset(bo.map, 0xa5, bytes);
      pack(&device, image, sampler);
      CHECK(PVR_IDFWDF_DATA_TEX == 0 && PVR_IDFWDF_DATA_SMP == 4);
      CHECK(PVR_IDFWDF_DATA_ADDR_LO == 8 && PVR_IDFWDF_DATA_ADDR_HI == 9);
      CHECK(bytes == 40);
      CHECK(memcmp(words, image.words, sizeof(image.words)) == 0);
      CHECK(memcmp(words + 4, sampler.words, sizeof(sampler.words)) == 0);
      CHECK(words[8] == (uint32_t)vma.dev_addr.addr);
      CHECK(words[9] == vma.dev_addr.addr >> 32);
   }
   free(bo.map);
   printf("PASS: %u checks; actual packing statements and shared shader ABI; no GPU execution\\n", checks);
   return 0;
}
C
File.write("#{work}/test.c", fixture)
cc = Shellwords.split(ENV.fetch('CC', 'cc'))
flags = Shellwords.split(ENV.fetch('IDFWDF_CFLAGS', '-O1 -g -fsanitize=address,undefined -fno-sanitize-recover=all'))
command = cc + %w[-std=c11 -Wall -Wextra -Werror] + flags + ["#{work}/test.c", '-o', "#{work}/test"]
File.write("#{work}/compile_commands.json", JSON.pretty_generate([{directory: work, file: "#{work}/test.c", arguments: command}]) + "\n")
File.write("#{work}/sources.json", JSON.pretty_generate(paths.to_h { |path| [path, Digest::SHA256.hexdigest(text.fetch(path))] }) + "\n")
output, status = Open3.capture2e(*command)
File.write("#{work}/build.log", output)
abort output unless status.success?
output, status = Open3.capture2e("#{work}/test")
File.write("#{work}/run.log", output)
puts output
abort "IDFWDF regression failed: #{status}" unless status.success?
