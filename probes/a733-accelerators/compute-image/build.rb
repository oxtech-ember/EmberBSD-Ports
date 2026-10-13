#!/usr/bin/env ruby
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EmberBSD contributors.
require 'json'
require 'shellwords'
require 'fileutils'
require 'digest'
abort 'usage: build.rb MESA MESA_BUILD OUTPUT' unless ARGV.size == 3
src, build, out = ARGV.map { |s| File.realpath(s) rescue File.expand_path(s) }
abort 'output already exists' if File.exist?(out)
FileUtils.mkdir_p(out)
script = File.expand_path(__dir__)
abort 'extract failed' unless system(RbConfig.ruby, File.join(script, 'extract.rb'), src, out)
entry = JSON.parse(File.read(File.join(build, 'compile_commands.json'))).find { |e| e['file'].end_with?('/pvr_device_info.c') }
abort 'real Mesa host compile command missing' unless entry
args = Shellwords.split(entry.fetch('command'))
cc = args.shift
skip = false
args = args.each_with_object([]) do |arg, a|
  if skip
    skip = false
  elsif %w[-o -MF -MQ -c].include?(arg)
    skip = true
  elsif %w[-MD -MMD].include?(arg)
    next
  elsif arg.start_with?('-I')
    a << '-I' + File.expand_path(arg[2..], build)
  elsif arg == '-O2'
    a << '-O1'
  else
    a << arg
  end
end
# All assertions stay enabled. Upstream warning options are unchanged.
args += ['-fsanitize=address,undefined', '-fno-omit-frame-pointer', '-DPVR_BUILD_ARCH_ROGUE',
         '-I'+out, '-I'+script, '-I'+File.join(src, 'src/imagination/vulkan'),
         '-I'+File.join(src, 'src/imagination/vulkan/pds'),
         '-I'+File.join(src, 'src/imagination/vulkan/pds/pvr_pds_programs')]
# Isolated patched host-header copy; shared Mesa source is never modified here.
iface = File.read(File.join(src, 'src/imagination/common/pvr_iface.h'))
if iface.include?("   PVR_IDFWDF_DATA_ADDR_LO,\n")
  iface = iface.sub("   PVR_IDFWDF_DATA_ADDR_LO,\n", "   /* The sampler occupies four shared-register dwords. */\n   PVR_IDFWDF_DATA_ADDR_LO = 8,\n")
end
abort 'IDFWDF layout not recognized' unless iface.include?('PVR_IDFWDF_DATA_ADDR_LO = 8,')
File.write(File.join(out, 'patched-pvr_iface.h'), iface)
files = [File.join(script, 'generate.c'), File.join(src, 'src/imagination/vulkan/pds/pvr_pds.c'),
         File.join(src, 'src/imagination/common/pvr_device_info.c')]
commands = []
objects = files.each_with_index.map do |file, i|
  object = File.join(out, "unit#{i}.o")
  command = [cc, *args, '-c', file, '-o', object]
  commands << {directory: build, arguments: command, file: file}
  ok = system(*command, chdir: build)
  File.write(File.join(out, 'compile_commands.json'), JSON.pretty_generate(commands)+"\n")
  abort "compile failed: #{file}" unless ok
  object
end
libs = %w[src/util/libmesa_util.a src/c11/impl/libmesa_util_c11.a]
link = [cc, '-isysroot', args[args.index('-isysroot') + 1], '-fsanitize=address,undefined', '-Wl,-dead_strip', *objects,
        *libs.map { |p| File.join(build, p) }, '-lc++', '-lz', '-o', File.join(out, 'generate')]
File.write(File.join(out, 'link.json'), JSON.pretty_generate(link)+"\n")
abort 'link failed' unless system(*link)
puts File.join(out, 'generate')
manifest = {
  mesa_version: '26.2.4',
  source_pins_sha256: Digest::SHA256.file(File.join(script, 'sources.tsv')).hexdigest,
  adapter_sha256: Digest::SHA256.file(File.join(script, 'generate.c')).hexdigest,
  extractor_sha256: Digest::SHA256.file(File.join(script, 'extract.rb')).hexdigest,
  generator_sha256: Digest::SHA256.file(File.join(out, 'generate')).hexdigest,
  generated_headers: %w[cdm cr pds vdm lls texstate].to_h { |name| [name, Digest::SHA256.file(File.join(build,"src/imagination/csbgen/rogue/#{name}.h")).hexdigest] },
  patched_iface_sha256: Digest::SHA256.file(File.join(out, 'patched-pvr_iface.h')).hexdigest,
  libraries: libs.to_h { |name| [name, Digest::SHA256.file(File.join(build,name)).hexdigest] },
  host_compiler: cc,
  host_compiler_version: IO.popen([cc, '--version'], &:read),
  instrumented: 'AddressSanitizer + UndefinedBehaviorSanitizer; linked Mesa utility archives are from the host build'
}
File.write(File.join(out, 'build-manifest.json'), JSON.pretty_generate(manifest)+"\n")
