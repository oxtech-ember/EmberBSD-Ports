#!/usr/bin/env ruby
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EmberBSD contributors. AI-assisted compiler closure.
require 'fileutils'
require 'json'
require 'open3'
require 'shellwords'
require_relative '../idfwdf/layout'
abort 'usage: generate-usclib.rb MESA_SOURCE MESA_BUILD SPIRV_DIS SPIRV_VAL NEW_OUT' unless ARGV.size == 5
mesa, build, dis, validator, out = ARGV.map { |p| File.expand_path(p) }
abort 'output already exists' if File.exist?(out)
abort 'Mesa version mismatch' unless File.read(mesa + '/VERSION').strip == '26.2.5'
upstream_environment = File.read(mesa + '/src/imagination/pco/uscgen/meson.build')
abort 'upstream common shader mode changed' unless upstream_environment.include?("env: ['PCO_DEBUG=no_pred_cf']")
header = Idfwdf.patched_header(mesa + '/src/imagination/common/pvr_iface.h')
line = File.readlines(build + '/build.ninja').find { |s| s.start_with?(' COMMAND = ') && s.include?('mesa_clc -o src/imagination/pco/usclib/pco_usclib.spv ') }
abort 'actual Mesa common compiler command missing' unless line
command = Shellwords.split(line.delete_prefix(' COMMAND = ').strip)
clc = build + '/src/compiler/clc/mesa_clc'
pco = build + '/src/imagination/pco/uscgen/pco_clc'
abort 'unexpected compiler in build command' unless File.realpath(command.first) == File.realpath(clc)
abort 'compiler argument delimiter missing' unless command.include?('--')
%w[common sync tex].each do |name|
  path = mesa + '/src/imagination/pco/usclib/' + name + '.cl'
  abort "compiler input missing: #{name}" unless command.any? { |a| !a.start_with?('-') && File.expand_path(a, build) == path }
end
FileUtils.mkdir_p(out + '/include/common')
File.write(out + '/include/common/pvr_iface.h', header)
spv = out + '/pco_usclib.spv'
command[command.index('-o') + 1] = spv
command[command.index('--depfile') + 1] = out + '/pco_usclib.d'
command.insert(command.index('--'), File.join(__dir__, 'cs-probe-store.cl'))
command.insert(command.index('--') + 1, '-I' + out + '/include')
commands = [command, [validator, spv], [dis, spv], [pco, spv, out + '/programs.h', out + '/programs.c']]
environments = commands.map { |argv| argv.first == pco ? { 'PCO_DEBUG' => 'no_pred_cf', 'PCO_DEBUG_PRINT' => 'cs,internal,nir,binary,verbose,stats' } : {} }
commands.each_with_index do |argv, n|
  environment = { 'TMPDIR' => ENV.fetch('TMPDIR') }.merge(environments[n])
  stdout, stderr, status = Open3.capture3(environment, *argv, chdir: build)
  File.write(out + "/step-#{n}.stdout", stdout)
  File.write(out + "/step-#{n}.stderr", stderr)
  File.write(out + '/commands.json', JSON.pretty_generate(commands) + "\n")
  abort "compiler step #{n} failed: #{status.inspect}" unless status.success?
  if n == 2
    File.write(out + '/pco_usclib.spvasm', stdout)
    Idfwdf.check_spirv(stdout)
    Idfwdf.check_probe(stdout)
  end
end
files = {
  'shared_header' => out + '/include/common/pvr_iface.h',
  'spirv' => spv, 'spirv_text' => out + '/pco_usclib.spvasm',
  'programs' => out + '/programs.c', 'programs_header' => out + '/programs.h',
  'mesa_clc' => clc, 'pco_clc' => pco, 'spirv_dis' => dis, 'spirv_val' => validator,
  'probe_source' => File.join(__dir__, 'cs-probe-store.cl'),
  'upstream_shader_build' => mesa + '/src/imagination/pco/uscgen/meson.build',
  'common_source' => mesa + '/src/imagination/pco/usclib/common.cl',
  'sync_source' => mesa + '/src/imagination/pco/usclib/sync.cl',
  'tex_source' => mesa + '/src/imagination/pco/usclib/tex.cl'
}
receipt = { 'schema' => 'ember-pco-usclib-v1', 'mesa_version' => '26.2.5',
  'idfwdf' => Idfwdf.check_spirv(File.read(out + '/pco_usclib.spvasm')),
  'probe' => Idfwdf.check_probe(File.read(out + '/pco_usclib.spvasm')),
  'files' => files.transform_values { |p| Idfwdf.file_record(p) },
  'commands' => commands, 'environments' => environments, 'hardware_validated' => false }
File.write(out + '/receipt.json', JSON.pretty_generate(receipt) + "\n")
puts "Generated common shaders with verified IDFWDF ABI: #{out}"
