#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted). Seal a real native Mesa build.
require 'digest'
require 'fileutils'
require 'json'
require 'open3'
require 'shellwords'

abort 'usage: seal-mesa-generators.rb MESA_ARCHIVE MESA_SOURCE MESA_BUILD SPIRV_VAL NEW_WORK' unless ARGV.size == 5
archive, source, build, validator = ARGV.first(4).map { |p| File.realpath(p) }
work = File.expand_path(ARGV.last)
abort 'Use new absolute paths without whitespace or shell metacharacters' unless ARGV.all? { |p| p.match?(%r{\A/[A-Za-z0-9_./-]+\z}) } && !File.exist?(work)
abort 'This native generator recipe requires macOS ARM64' unless RUBY_PLATFORM.include?('darwin') && `uname -m`.strip == 'arm64'
owner = File.dirname(File.realpath(__FILE__))
ports = File.expand_path('../../..', owner)
recipe = owner + '/../recipes/graphics/MesaLib'
sha = ->(p) { Digest::SHA256.file(p).hexdigest }
pin = 'bce5f7fbebb934373b86c999a064d52fb5065878dc57f287f95346648ec832e9'
abort 'Wrong Mesa source archive' unless sha.call(archive) == pin
abort 'Wrong Mesa source version' unless File.read(source + '/VERSION').strip == '26.2.4'
metadata = build + '/meson-info'
info = JSON.parse(File.read(metadata + '/meson-info.json'))
abort 'Native build uses another source tree' unless File.realpath(info.fetch('directories').fetch('source')) == source
project = JSON.parse(File.read(metadata + '/intro-projectinfo.json'))
abort 'Wrong Mesa build version' unless project.fetch('version') == '26.2.4'
options = JSON.parse(File.read(metadata + '/intro-buildoptions.json')).to_h { |o| [o.fetch('name'), o.fetch('value')] }
abort 'Native tools must retain assertions' unless options.fetch('b_ndebug') == 'false'
abort 'Native tools must use LLVM23' unless File.read(build + '/build.ninja').include?('23.1.3')
tools = {'mesa_clc' => 'src/compiler/clc/mesa_clc', 'vtn_bindgen2' => 'src/compiler/spirv/vtn_bindgen2', 'pco_clc' => 'src/imagination/pco/uscgen/pco_clc'}
tools.each_value do |path|
    file = build + '/' + path
    abort "Missing real native tool: #{file}" unless File.executable?(file) && File.binread(file, 8).unpack('V2') == [0xfeedfacf, 0x0100000c]
    deps, status = Open3.capture2e('otool', '-L', file)
    abort "Cannot inspect #{file}" unless status.success?
    abort "Unrecorded non-system shared dependency: #{file}" unless deps.lines.drop(1).all? { |line| line.strip.start_with?('/usr/lib/', '/System/Library/') }
end
abort 'Missing SPIR-V validator' unless File.executable?(validator)
# Capture the actual toolchain, static libraries and command metadata before use.
inputs = [__FILE__, archive, validator, build + '/build.ninja', build + '/compile_commands.json']
targets = JSON.parse(File.read(metadata + '/intro-targets.json'))
tools.each do |name, path|
    selected = targets.find { |t| t.fetch('name') == name && t.fetch('type') == 'executable' }
    abort "Missing real Meson target: #{name}" unless selected && selected.fetch('filename') == [build + '/' + path]
    inputs << build + '/' + path
    selected.fetch('target_sources').each do |group|
        inputs.concat(group.fetch('compiler', []))
        inputs.concat(group.fetch('linker', []))
        group.fetch('parameters', []).each do |arg|
            inputs << File.expand_path(arg, build) if arg.end_with?('.a', '.tbd')
        end
    end
end
inputs.concat(Dir.glob(metadata + '/*.json'))
inputs.uniq!
input_hashes = inputs.to_h { |p| [p, sha.call(p)] }
FileUtils.mkdir_p(work + '/reference')
commands = []
run = lambda do |argv, name, environment = {}|
    commands << {'argv' => argv, 'cwd' => build, 'environment' => environment}
    out, err, status = Open3.capture3(environment, *argv, chdir: build)
    File.write(work + "/#{name}.stdout", out)
    File.write(work + "/#{name}.stderr", err)
    abort "Generator step failed: #{name}" unless status.success?
    out
end
run.call(['tar', '-xf', archive, '--strip-components=1', '-C', work + '/reference'], 'extract')
# The native helper's only permitted source delta adds an exact BVNC selector.
# The ICD build uses no diagnostic shaders and leaves this selector unused.
bvnc_patch = ports + '/probes/a733-accelerators/host-tools/mesa-26.2.4-pco-bvnc.patch'
ref_pco = work + '/reference/src/imagination/pco/uscgen/pco_clc.c'
if sha.call(ref_pco) != sha.call(source + '/src/imagination/pco/uscgen/pco_clc.c')
    run.call(['patch', '-f', '-N', '-F', '0', '-p1', '-d', work + '/reference', '-i', bvnc_patch], 'bvnc-patch')
end
source_rows = []
Dir.glob(work + '/reference/**/*', File::FNM_DOTMATCH).sort.each do |p|
    next unless File.file?(p)
    relative = p.delete_prefix(work + '/reference/')
    actual = source + '/' + relative
    abort "Native source differs from the pinned source: #{relative}" unless File.file?(actual) && sha.call(p) == sha.call(actual)
    source_rows << "#{sha.call(actual)}  #{relative}\n"
end
File.write(work + '/source.sha256', source_rows.join)
FileUtils.mkdir_p([work + '/bin', work + '/smoke', work + '/metadata'])
tools.each { |name, p| FileUtils.cp(build + '/' + p, work + '/bin/' + name) }
%w[meson-info.json intro-projectinfo.json intro-buildoptions.json intro-targets.json intro-dependencies.json].each { |name| FileUtils.cp(metadata + '/' + name, work + '/metadata/' + name) }
%w[build.ninja compile_commands.json].each { |name| FileUtils.cp(build + '/' + name, work + '/metadata/' + name) }
# The runtime and generated common programs consume this same reviewed header.
run.call(['patch', '-f', '-N', '-F', '0', '-p0', '-d', work + '/reference', '-i', recipe + '/patches/patch-src_imagination_common_pvr__iface.h'], 'interface-patch')
interfaces = %w[src/compiler/nir/nir.h src/compiler/nir/nir_serialize.c src/compiler/nir/nir_intrinsics.py src/compiler/spirv/spirv_to_nir.c src/imagination/common/pvr_iface.h src/imagination/pco/pco.h src/imagination/pco/pco_common.h.py src/imagination/pco/usclib/common.cl src/imagination/pco/usclib/sync.cl src/imagination/pco/usclib/tex.cl]
File.write(work + '/interface.sha256', interfaces.map { |p| "#{sha.call(work + '/reference/' + p)}  #{p}\n" }.join)
line = File.readlines(build + '/build.ninja').find { |s| s.start_with?(' COMMAND = ') && s.include?('mesa_clc -o src/imagination/pco/usclib/pco_usclib.spv ') }
abort 'Missing genuine upstream common-shader command' unless line
argv = Shellwords.split(line.delete_prefix(' COMMAND = ').strip)
abort 'Unexpected build compiler' unless File.realpath(argv.first) == File.realpath(build + '/' + tools.fetch('mesa_clc'))
abort 'Missing compiler delimiter' unless argv.include?('--')
inputs = argv[1...argv.index('--')].reject { |a| a.start_with?('-') }
abort 'Unexpected shader source in native command' unless inputs.grep(/\.cl\z/).size == 3
%w[common sync tex].each do |name|
    abort 'Incomplete common shader inputs' unless inputs.any? { |a| File.expand_path(a, build) == source + '/src/imagination/pco/usclib/' + name + '.cl' }
end
argv[0] = work + '/bin/mesa_clc'
argv[argv.index('-o') + 1] = work + '/smoke/pco_usclib.spv'
argv[argv.index('--depfile') + 1] = work + '/smoke/pco_usclib.d'
argv.insert(argv.index('--') + 1, '-I' + work + '/reference/src/imagination')
# Discover implicit Clang resource headers and generated includes with the real
# compiler. Only the subsequent compile is accepted, after all inputs are sealed.
discovery = argv.dup
discovery[discovery.index('-o') + 1] = work + '/smoke/discovery.spv'
discovery[discovery.index('--depfile') + 1] = work + '/smoke/discovery.d'
# Pinned clc_helpers.cpp remaps exactly two built-in OpenCL headers. Require
# the real static-header build flag and bind their generated source arrays.
clc_command = JSON.parse(File.read(build + '/compile_commands.json')).find { |c| File.expand_path(c.fetch('file'), c.fetch('directory')) == source + '/src/compiler/clc/clc_helpers.cpp' }
abort 'Native CLC does not embed its OpenCL headers' unless clc_command && Shellwords.split(clc_command.fetch('command')).include?('-DUSE_STATIC_OPENCL_C_H=1')
FileUtils.mkdir_p(work + '/tmp')
compile_environment = {'TMPDIR' => work + '/tmp'}
virtual_headers = %w[opencl-c-base.h opencl-c.h].to_h { |name| [work + '/tmp/openclon12/' + name, File.realpath(build + '/src/compiler/clc/' + name + '.h')] }
input_hashes.merge!(virtual_headers.values.to_h { |p| [p, sha.call(p)] })
run.call(discovery, 'common-discover', compile_environment)

read_deps = lambda do |path|
    text = File.read(path).gsub(/\\\n/, ' ')
    Shellwords.split(text.split(':', 2).fetch(1)).map do |p|
        path = File.expand_path(p, build)
        virtual_headers.fetch(path) { File.realpath(path) }
    end.uniq.sort
end
deps = read_deps.call(work + '/smoke/discovery.d')
abort 'Empty common shader dependency set' if deps.empty?
shader_hashes = deps.to_h { |p| [p, sha.call(p)] }
run.call(argv, 'common-clc', compile_environment)
abort 'Common shader dependency set changed' unless read_deps.call(work + '/smoke/pco_usclib.d') == deps
deps.each do |p|
    abort "Common shader dependency changed: #{p}" unless sha.call(p) == shader_hashes.fetch(p)
end
File.write(work + '/shader-inputs.json', JSON.pretty_generate(shader_hashes) + "\n")
run.call([validator, work + '/smoke/pco_usclib.spv'], 'common-validate')
run.call([work + '/bin/vtn_bindgen2', work + '/smoke/pco_usclib.spv', work + '/smoke/pco_usclib.cpp', work + '/smoke/pco_usclib.h'], 'common-nir')
run.call([work + '/bin/pco_clc', work + '/smoke/pco_usclib.spv', work + '/smoke/pco_uscgen_programs.h', work + '/smoke/pco_uscgen_programs.c'], 'common-pco', {'PCO_DEBUG' => 'no_pred_cf'})
%w[pco_usclib.spv pco_usclib.cpp pco_usclib.h pco_uscgen_programs.h pco_uscgen_programs.c].each do |p|
    abort "Empty generated output: #{p}" unless File.size(work + '/smoke/' + p).positive?
end
input_hashes.merge!(deps.to_h { |p| [p, shader_hashes.fetch(p)] })
input_hashes.each do |path, expected|
    abort "Native build changed during sealing: #{path}" unless sha.call(path) == expected
end
source_rows.each do |row|
    expected, relative = row.chomp.split('  ', 2)
    abort "Native source changed during sealing: #{relative}" unless sha.call(source + '/' + relative) == expected
end
[bvnc_patch, recipe + '/patches/patch-src_imagination_common_pvr__iface.h'].each { |p| input_hashes[p] = sha.call(p) }
receipt = {'schema' => 'ember-mesa-generators-1', 'mesa' => '26.2.4', 'llvm' => '23.1.3', 'source' => source, 'build' => build,
           'archive_sha256' => pin, 'commands' => commands, 'inputs' => input_hashes, 'virtual_headers' => virtual_headers,
           'scope' => 'Pinned native source, real compiled tools, full common OpenCL to SPIR-V/NIR/PCO generation. No target execution.'}
File.write(work + '/receipt.json', JSON.pretty_generate(receipt) + "\n")
File.write(work + '/FORMAT', "ember-mesa-generators-1\n")
# Keep evidence, but the extracted reference is not part of the sealed tools.
FileUtils.rm_r(work + '/reference')
files = Dir.glob(work + '/**/*').select { |p| File.file?(p) }.sort
File.write(work + '/installed.sha256', files.map { |p| "#{sha.call(p)}  #{p.delete_prefix(work + '/')}\n" }.join)
puts "PASS: sealed native Mesa 26.2.4 generators: #{work}"
