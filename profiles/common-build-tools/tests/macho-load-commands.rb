#!/usr/bin/env ruby
# Real Mach-O regressions for the opt-in pkgsrc dependency resolver.
require 'fileutils'
require 'open3'

abort 'usage: macho-load-commands.rb PREPARED_PKGSRC NEW_WORK' unless ARGV.size == 2
machine, status = Open3.capture2('uname', '-sm')
abort 'Apple Silicon macOS required' unless status.success? && machine.strip == 'Darwin arm64'
pkgsrc = File.realpath(ARGV[0])
work = File.expand_path(ARGV[1])
abort 'new absolute work directory required' unless ARGV[1].start_with?('/') && !File.exist?(work)
FileUtils.mkdir_p(work)
script = File.join(pkgsrc, 'mk/check/check-shlibs-macho.awk')
prefix = '/ember-macho-contract'
stage = File.join(work, 'stage')
root = stage + prefix
FileUtils.mkdir_p([root + '/bin', root + '/lib'])
File.write(work + '/provider.c', 'int answer(void) { return 42; }')
File.write(work + '/consumer.c', 'int answer(void); int main(void) { return answer() != 42; }')
run = lambda do |*args|
  out, status = Open3.capture2e(*args)
  abort "#{args.inspect}: #{out}" unless status.success?
  out
end
run.call('cc', '-dynamiclib', work + '/provider.c', '-Wl,-install_name,@rpath/libanswer.dylib', '-o', root + '/lib/libanswer.dylib')
run.call('cc', work + '/consumer.c', '-L' + root + '/lib', '-lanswer', '-Wl,-headerpad_max_install_names', '-Wl,-rpath,@loader_path/../lib', '-o', root + '/bin/consumer')
run.call(root + '/bin/consumer')
File.write(work + '/depends', '')
env = {'MACHO_OD' => ENV.fetch('MACHO_OD'),
       'MACHO_LIPO' => ENV.fetch('MACHO_LIPO'),
       'MACHO_OTOOL' => ENV.fetch('MACHO_OTOOL'), 'DESTDIR' => stage, 'PREFIX' => prefix, 'WRKDIR' => work,
       'SKIP_SYSTEM_LIBS' => '1', 'MACHO_USE_LOAD_COMMANDS' => 'yes',
       'PKG_INFO_CMD' => '/usr/bin/false', 'DEPENDS_FILE' => work + '/depends'}
check = lambda do |name, files, expected, overrides = {}|
  requires = work + '/' + name + '.requires'
  File.write(requires, '')
  output, status = Open3.capture2e(env.merge('REQUIRES_FILE' => requires).merge(overrides),
    'awk', '-f', script, stdin_data: files.join("\n") + "\n", chdir: root)
  File.write(work + '/' + name + '.log', output)
  abort "#{name}: checker failed: #{output}" unless status.success?
  abort "#{name}: unexpected diagnostic #{output}" unless expected ? output.include?(expected) : output.empty?
  File.readlines(requires, chomp: true).uniq
end
abort 'self ID emitted as an import' unless check.call('identity', ['lib/libanswer.dylib'], nil).empty?
abort 'wrong direct requirement' unless check.call('relative', ['bin/consumer', 'lib/libanswer.dylib'], nil) == [prefix + '/lib/libanswer.dylib']
check.call('legacy-negative', ['lib/libanswer.dylib'], 'relative library path: @rpath/libanswer.dylib', {'MACHO_USE_LOAD_COMMANDS' => ''})
FileUtils.mv(root + '/lib/libanswer.dylib', root + '/lib/saved.dylib')
check.call('missing-provider', ['bin/consumer'], 'unresolved library path: @rpath/libanswer.dylib')
FileUtils.mv(root + '/lib/saved.dylib', root + '/lib/libanswer.dylib')
run.call('install_name_tool', '-delete_rpath', '@loader_path/../lib', root + '/bin/consumer')
check.call('missing-runpath', ['bin/consumer'], 'unresolved library path: @rpath/libanswer.dylib')
run.call('install_name_tool', '-change', '@rpath/libanswer.dylib', '@loader_path/../lib/libanswer.dylib', root + '/bin/consumer')
check.call('direct-loader', ['bin/consumer'], nil)
run.call('install_name_tool', '-change', '@loader_path/../lib/libanswer.dylib', '@executable_path/../lib/libanswer.dylib', root + '/bin/consumer')
check.call('direct-executable', ['bin/consumer'], nil)
run.call('cc', '-arch', 'x86_64', '-dynamiclib', work + '/provider.c', '-Wl,-install_name,@rpath/libanswer.dylib', '-o', work + '/x86.dylib')
FileUtils.mkdir_p(root + '/wrong-arch')
FileUtils.cp(work + '/x86.dylib', root + '/wrong-arch/libanswer.dylib')
run.call('cc', work + '/consumer.c', '-L' + root + '/lib', '-lanswer',
  '-Wl,-rpath,@loader_path/../wrong-arch', '-Wl,-rpath,@loader_path/../lib', '-o', root + '/bin/fallback')
run.call(root + '/bin/fallback')
abort 'wrong runpath choice' unless check.call('architecture-fallback', ['bin/fallback'], nil) == [prefix + '/lib/libanswer.dylib']
run.call('lipo', '-create', root + '/lib/libanswer.dylib', work + '/x86.dylib', '-output', root + '/lib/libuniversal.dylib')
abort 'universal IDs emitted as imports' unless check.call('universal', ['lib/libuniversal.dylib'], nil).empty?
FileUtils.mv(root + '/lib/libanswer.dylib', root + '/lib/arm-saved.dylib')
FileUtils.cp(work + '/x86.dylib', root + '/lib/libanswer.dylib')
check.call('wrong-architecture', ['bin/consumer'], 'incompatible library architecture arm64:')
FileUtils.mv(root + '/lib/arm-saved.dylib', root + '/lib/libanswer.dylib')
FileUtils.cp(root + '/lib/libanswer.dylib', root + '/bin/libanswer.dylib')
run.call('install_name_tool', '-change', '@executable_path/../lib/libanswer.dylib', '@rpath/libanswer.dylib', '-add_rpath', '@loader_path', root + '/bin/consumer')
check.call('bare-loader-runpath', ['bin/consumer'], nil)
run.call('install_name_tool', '-delete_rpath', '@loader_path', '-add_rpath', '@executable_path', root + '/bin/consumer')
check.call('bare-executable-runpath', ['bin/consumer'], nil)
FileUtils.cp(root + '/lib/libanswer.dylib', work + '/external.dylib')
run.call('install_name_tool', '-change', '@rpath/libanswer.dylib', work + '/external.dylib', root + '/bin/consumer')
File.write(work + '/pkg-info', "#!/bin/sh\nprintf 'provider-1.0\\n'\n")
File.chmod(0o755, work + '/pkg-info')
external_env = {'WRKDIR' => work + '/separate-work', 'PKG_INFO_CMD' => work + '/pkg-info'}
check.call('undeclared-owner', ['bin/consumer'], 'is not a runtime dependency', external_env)
File.write(work + '/depends', "build provider>=1.0 provider-1.0\n")
check.call('build-only-owner', ['bin/consumer'], 'is not a runtime dependency', external_env)
File.write(work + '/depends', "full provider>=1.0 provider-1.0\n")
check.call('runtime-owner', ['bin/consumer'], nil, external_env)
run.call('install_name_tool', '-change', work + '/external.dylib', work + '/leak.dylib', root + '/bin/consumer')
check.call('work-reference', ['bin/consumer'], 'path relative to WRKDIR:')
puts 'PASS: runtime, self-ID exclusion, per-architecture runpaths and fallback, loader/executable paths, missing provider/runpath, wrong architecture, dependency ownership and work-reference refusals; default legacy path retained'
