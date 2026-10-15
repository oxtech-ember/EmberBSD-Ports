#!/usr/bin/env ruby
# SPDX-License-Identifier: MIT
require 'optparse'
require 'shellwords'
require 'open3'
require 'fileutils'
require 'digest'
require 'json'

options = {cc: ENV.fetch('CC', 'cc'), cxx: ENV.fetch('CXX', 'c++'), objcopy: 'objcopy', readelf: 'readelf', run: false}
parser = OptionParser.new do |p|
  p.banner = 'Usage: ruby run.rb --prefix SDK --baseline-header FILE --patched-header FILE --work DIR [--run]'
  %i[prefix baseline_header patched_header work cc cxx objcopy readelf].each do |key|
    p.on("--#{key.to_s.tr('_','-')} VALUE") { |value| options[key] = value }
  end
  p.on('--run') { options[:run] = true }
end
parser.parse!
abort parser.to_s unless ARGV.empty? && %i[prefix baseline_header patched_header work].all? { |k| options[k] }
%w[prefix baseline_header patched_header work].each { |k| options[k.to_sym] = File.expand_path(options.fetch(k.to_sym)) }
work = options.fetch(:work)
abort 'Work directory must be absent or empty' if File.exist?(work) && !Dir.empty?(work)
FileUtils.mkdir_p(work)
records = []
run = lambda do |name, args, env = {}|
  out, err, status = Open3.capture3(env, *args)
  File.write(File.join(work, name + '.stdout'), out)
  File.write(File.join(work, name + '.stderr'), err)
  record = {name: name, command: args, environment: env, exit: status.exitstatus}
  records << record
  File.write(File.join(work, 'commands.json'), JSON.pretty_generate(records) + "\n")
  [out, err, status]
end
%i[cc cxx].each do |kind|
  version, error, status = run.call("compiler-version-#{kind}", [options.fetch(kind), '-dumpfullversion', '-dumpversion'])
  abort "GCC16 required for #{kind}: #{version}#{error}" unless status.success? && version.start_with?('16.')
end
pkg_env = {'PKG_CONFIG_LIBDIR' => File.join(options.fetch(:prefix),'lib/pkgconfig'),
           'PKG_CONFIG_PATH' => '', 'PKG_CONFIG_SYSROOT_DIR' => ''}
cflags, error, status = run.call('pkg-config', ['pkg-config','--cflags','ncnn'], pkg_env)
abort "pkg-config failed: #{error}" unless status.success?
flags = Shellwords.split(cflags)
abort 'Expected the actual pkg-config ordinary include path' unless flags.any? { |f| f.start_with?('-I') } && flags.none? { |f| f.start_with?('-isystem') }
inputs = {}
%w[before after].each do |profile|
  dir = File.join(work,profile,'include/ncnn')
  FileUtils.mkdir_p(dir)
  header = options.fetch(profile == 'before' ? :baseline_header : :patched_header)
  {'c_api.h' => header,
   'platform.h' => File.join(options.fetch(:prefix),'include/ncnn/platform.h'),
   'ncnn_export.h' => File.join(options.fetch(:prefix),'include/ncnn/ncnn_export.h')}.each do |name, path|
    FileUtils.cp(path,File.join(dir,name))
    inputs[path] = Digest::SHA256.file(path).hexdigest
  end
end
source = File.join(__dir__,'layout.c')
exports = File.join(__dir__,'exports.c')
[source, exports, __FILE__].each { |path| inputs[path] = Digest::SHA256.file(path).hexdigest }
strict = %w[-O2 -Wall -Wextra -Wpedantic -Werror -fvisibility=hidden]
profile_args = lambda do |profile, language|
  [language == 'c' ? options.fetch(:cc) : options.fetch(:cxx), '-x',language,
   language == 'c' ? '-std=c11' : '-std=c++17', *strict,
   "-I#{File.join(work,profile,'include')}", *flags]
end
_, baseline_error, baseline_status = run.call('before-c-failure',[*profile_args.call('before','c'),'-c',source,'-o',File.join(work,'before-c.o')])
diagnostics = baseline_error.lines.select { |line| line.include?('attribute ignored on types') && line.include?('visibility') }
errors = baseline_error.lines.select { |line| line.include?(': error:') }
abort 'Baseline C did not fail on exactly four type-visibility errors' unless !baseline_status.success? && diagnostics.size == 4 && errors == diagnostics
variants = [['before','c++','before-cxx'],['after','c','after-c'],['after','c++','after-cxx']]
sections = []
runs = []
variants.each do |profile, language, label|
  args = profile_args.call(profile,language)
  object = File.join(work,label+'.o')
  _, err, s = run.call(label+'-compile', [*args,'-c',source,'-o',object])
  abort "Strict compile failed #{label}: #{err}" unless s.success?
  binary = File.join(work,label)
  _, err, s = run.call(label+'-link', [language == 'c' ? options.fetch(:cc) : options.fetch(:cxx),object,'-o',binary])
  abort "Link failed #{label}: #{err}" unless s.success?
  section = File.join(work,label+'.abi')
  _, err, s = run.call(label+'-section',[options.fetch(:objcopy),'--dump-section',".ncnn_abi=#{section}",object])
  abort "Section extraction failed #{label}: #{err}" unless s.success?
  sections << File.binread(section)
  library = File.join(work,label+'-exports.so')
  _, err, s = run.call(label+'-exports',[*args,'-fPIC','-shared',exports,'-o',library])
  abort "Function export compile failed #{label}: #{err}" unless s.success?
  symbols, err, s = run.call(label+'-symbols',[options.fetch(:readelf),'--dyn-syms','--wide',library])
  abort "Symbol inspection failed #{label}: #{err}" unless s.success?
  %w[ncnn_version ncnn_version_number].each do |name|
    abort "Function export lost #{label}: #{name}" unless symbols.lines.any? { |line| line.match?(/\bGLOBAL\s+DEFAULT\s+\d+\s+#{name}\s*$/) }
  end
  if options[:run]
    out, err, s = run.call(label+'-run',[binary])
    abort "Execution failed #{label}: #{err}" unless s.success?
    runs << out
  end
end
abort 'C/C++ object layout differs from the original C++ ABI' unless sections.uniq.size == 1
abort 'Native C/C++ layout output differs' if options[:run] && runs.uniq.size != 1
# Apart from the four conditional type declarations, every token is preserved.
before = File.read(options.fetch(:baseline_header))
after = File.read(options.fetch(:patched_header))
%w[allocator datareader modelbin layer].each do |type|
  conditional = "#ifdef __cplusplus\nstruct NCNN_EXPORT __ncnn_#{type}_t\n#else\nstruct __ncnn_#{type}_t\n#endif\n"
  abort "Unexpected type repair #{type}" unless after.scan(conditional).size == 1
  after.sub!(conditional,"struct NCNN_EXPORT __ncnn_#{type}_t\n")
end
abort 'An unrelated public declaration changed' unless after == before
summary = {baseline_c_visibility_errors: diagnostics.size, abi_variants: variants.map(&:last),
           identical_layout_bytes: sections.first.bytesize, layout_sha256: Digest::SHA256.hexdigest(sections.first),
           native_executions: runs.size, compiler_environment: {'EMBERBSD_SYSROOT' => ENV['EMBERBSD_SYSROOT']}.compact, preserved_function_exports: %w[ncnn_version ncnn_version_number],
           input_sha256: inputs}
File.write(File.join(work,'result.json'),JSON.pretty_generate(summary)+"\n")
puts JSON.generate(summary)
