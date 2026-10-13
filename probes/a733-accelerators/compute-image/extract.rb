#!/usr/bin/env ruby
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EmberBSD contributors.
# Extract unchanged producers. This does not generate GPU instructions.
require 'digest'
require 'json'
abort 'usage: extract.rb MESA OUTPUT' unless ARGV.length == 2
root, out = ARGV.map { |p| File.expand_path(p) }
pins = File.readlines(File.join(__dir__, 'sources.tsv')).reject { |l| l.start_with?('#') || l.strip.empty? }
pins.each do |line|
  expected, path = line.strip.split("	", 2)
  data = File.binread(File.join(root, path))
  # Only this separately reviewed downstream header change is permitted.
  if path.end_with?('/pvr_iface.h')
    data = data.sub("   /* The sampler occupies four shared-register dwords. */\n   PVR_IDFWDF_DATA_ADDR_LO = 8,\n", "   PVR_IDFWDF_DATA_ADDR_LO,\n")
  end
  abort "source pin mismatch: #{path}" unless Digest::SHA256.hexdigest(data) == expected
end
base = File.join(root, 'src/imagination/vulkan')

# C lexer sufficient for braces outside comments and string/character literals.
def block(text, start)
  open = text.index('{', start) or abort 'missing opening brace'
  depth = 0
  text[open..].to_enum(:scan, %r{/\*.*?\*/|//[^\n]*|"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*'|[{}]}m).each do
    token = Regexp.last_match[0]
    depth += 1 if token == '{'
    depth -= 1 if token == '}'
    return text[start...(open + Regexp.last_match.end(0))] if depth.zero?
  end
  abort 'unterminated C block'
end

def function(text, name)
  m = /(?:^static [\w *]+\n|^static |^)(?:[\w *]+\s+)?#{Regexp.escape(name)}\s*\(/m.match(text)
  abort "missing function #{name}" unless m
  # Select signature from previous blank line, excluding preceding comments.
  start = text.rindex("\n\n", m.begin(0))
  start = start ? start + 2 : 0
  candidate = text[start...m.begin(0)]
  start = m.begin(0) if candidate.include?('*/')
  block(text, start)
end

def struct(text, name)
  m = /\bstruct #{Regexp.escape(name)}\s*\{/.match(text) or abort "missing struct #{name}"
  block(text, m.begin(0)) + ';'
end

spec = {
  'pvr_border.h' => [:struct, %w[pvr_border_color_table]],
  'pvr_common.h' => [:struct, %w[pvr_pds_upload]],
  'pvr_job_context.h' => [:struct, %w[rogue_sr_programs pvr_compute_ctx]],
  'pvr_pipeline.h' => [:struct, %w[pvr_private_compute_pipeline]],
  'pvr_arch_cmd_buffer.c' => [:struct, %w[pvr_compute_kernel_info]],
  'winsys/pvr_winsys.h' => [:struct, %w[pvr_rogue_winsys_compute_ctx_static_state pvr_winsys_compute_submit_info]]
}
File.open(File.join(out, 'mesa-types.h'), 'w') do |f|
  f.puts '/* Unchanged Mesa 26.2.4 declarations. See source-hashes.json. */'
  border = File.read(File.join(base, 'pvr_border.h'))
  %w[PVR_BORDER_COLOR_TABLE_NR_ENTRIES PVR_BORDER_COLOR_TABLE_NR_BUILTIN_ENTRIES].each do |name|
    definition = border[/^#define #{name} \\\n[^\n]+/] or abort 'missing border constant'
    f.puts definition
  end
  drm = File.read(File.join(root, 'include/drm-uapi/pvr_drm.h'))
  %w[PREVENT_ALL_OVERLAP SINGLE_CORE].each do |suffix|
    definition = drm[/^#define DRM_PVR_SUBMIT_JOB_COMPUTE_CMD_#{suffix} [^\n]+/] or abort 'missing DRM flag'
    f.puts definition
  end
  spec.each do |file, (_, names)|
    data = File.read(File.join(base, file))
    names.each { |name| f.puts struct(data, name) }
  end
end
functions = {
  'pvr_arch_device.c' => %w[pvr_arch_pds_compute_shader_create_and_upload pvr_pds_idfwdf_programs_create_and_upload],
  'pvr_arch_job_context.c' => %w[pvr_pds_ctx_sr_program_setup pvr_pds_compute_ctx_sr_program_create_and_upload pvr_pds_sr_fence_terminate_program_create_and_upload pvr_compute_ctx_ws_static_state_init],
  'pvr_arch_job_compute.c' => %w[pvr_submit_info_stream_init pvr_submit_info_flags_init],
  'winsys/powervr/pvr_drm_job_compute.c' => %w[pvr_winsys_compute_flags_to_drm],
  'pvr_arch_cmd_buffer.c' => %w[pvr_compute_flat_slot_size pvr_compute_generate_control_stream pvr_compute_generate_idfwdf pvr_arch_compute_generate_fence pvr_compute_flat_pad_workgroup_size pvr_arch_compute_update_kernel_private]
}
File.open(File.join(out, 'mesa-producers.h'), 'w') do |f|
  f.puts '/* Unchanged Mesa 26.2.4 producers. See source-hashes.json. */'
  functions.each do |file, names|
    data = File.read(File.join(base, file))
    names.each { |name| body = function(data, name); f.puts(body[0...body.index("{")].strip + ";") unless body.start_with?("static"); f.puts body }
  end
end
hashes = (spec.keys + functions.keys).uniq.to_h { |file| ["src/imagination/vulkan/#{file}", Digest::SHA256.file(File.join(base, file)).hexdigest] }
File.write(File.join(out, 'source-hashes.json'), JSON.pretty_generate(hashes) + "\n")
runtime_path = File.join(root, 'src/imagination/drm-shim/pvr_noop.c')
runtime = File.read(runtime_path)
File.open(File.join(out, 'mesa-runtime.h'), 'w') do |f|
  f.puts '/* Unchanged Mesa runtime-info formula. No DRM shim is executed. */'
  %w[rogue_num_phantoms rogue_common_store_partition_space_size rogue_common_store_alloc_region_size rogue_max_coeffs rogue_cdm_max_local_mem_size_regs].each do |name|
    f.puts function(runtime, name)
  end
end
hashes['src/imagination/drm-shim/pvr_noop.c'] = Digest::SHA256.file(runtime_path).hexdigest
File.write(File.join(out, 'source-hashes.json'), JSON.pretty_generate(hashes) + "\n")
data_path = File.join(root, 'src/imagination/pco/pco_data.h')
data = File.read(data_path)
prefix = data[/typedef struct PACKED _pco_precomp_data \{.*?\} pco_precomp_data;\nstatic_assert\([^;]+;/m] or abort 'precompiled data declaration missing'
File.write(File.join(out, 'mesa-precomp.h'), prefix + "\n")
hashes['src/imagination/pco/pco_data.h'] = Digest::SHA256.file(data_path).hexdigest
File.write(File.join(out, 'source-hashes.json'), JSON.pretty_generate(hashes) + "\n")

# Preserve the border tables and their packing functions byte for byte.
border_path = File.join(base, 'pvr_arch_border.c')
border = File.read(border_path)
File.open(File.join(out, 'mesa-border.h'), 'w') do |f|
  f.puts '/* Unchanged Mesa border producer and format helpers. */'
  format = File.read(File.join(root, 'src/vulkan/util/vk_format.c'))
  map_start = format.index('const enum pipe_format vk_format_map[] = {') or abort 'missing format map'
  f.puts block(format, map_start) + ';'
  %w[vk_format_to_pipe_format vk_format_aspects].each { |name| f.puts function(format, name) }
  sampler = File.read(File.join(root, 'src/vulkan/runtime/vk_sampler.c'))
  %w[vk_border_color_value vk_border_color_is_int].each do |name|
    body = function(sampler, name)
    f.puts body[0...body.index('{')].strip + ';'
    f.puts body
  end
  f.puts function(File.read(File.join(base, 'pvr_formats.c')), 'pvr_get_format_swizzle_for_tpu')
  first = border.index('struct pvr_border_color_table_value {') or abort 'missing border tables'
  last = border.index("static int32_t\npvr_border_color_table_alloc_entry", first) or abort 'missing border table boundary'
  f.puts border[first...last]
  %w[pvr_invert_swizzle pvr_border_color_swizzle_to_tex_format pvr_border_color_table_fill_entry pvr_arch_border_color_table_init].each do |name|
    body = function(border, name)
    f.puts body[0...body.index('{')].strip + ';' unless body.start_with?('static')
    f.puts body
  end
end
%w[src/vulkan/util/vk_format.c src/vulkan/runtime/vk_sampler.c src/imagination/vulkan/pvr_formats.c src/imagination/vulkan/pvr_arch_border.c].each do |path|
  hashes[path] = Digest::SHA256.file(File.join(root, path)).hexdigest
end
File.write(File.join(out, 'source-hashes.json'), JSON.pretty_generate(hashes) + "\n")

license = File.read(File.join(__dir__, 'LICENSE'))
%w[mesa-types.h mesa-producers.h mesa-runtime.h mesa-precomp.h mesa-border.h].each do |name|
  path = File.join(out, name)
  File.write(path, "/*\n" + license.lines.map { |line| " * " + line }.join + " */\n" + File.read(path))
end
