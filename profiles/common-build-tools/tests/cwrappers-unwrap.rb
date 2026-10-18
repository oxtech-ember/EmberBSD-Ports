#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), real compiler-wrapper metadata regression.
require 'digest'
require 'fileutils'
require 'json'
require 'open3'
require 'shellwords'

abort 'Usage: cwrappers-unwrap.rb PKGSRC NATIVE_PREFIX LIBTOOL NEW_WORK' unless ARGV.length == 4
tree, prefix, libtool = ARGV.first(3).map { |p| File.realpath(p) }
work = File.expand_path(ARGV.last)
abort 'Use absolute portable paths' unless [tree, prefix, libtool, work].all? { |p| p.match?(%r{\A/[A-Za-z0-9_./+-]+\z}) }
abort 'Output exists' if File.exist?(work) || File.symlink?(work)
FileUtils.mkdir(work)
cc = Shellwords.split(ENV.fetch('CC', 'gcc'))
make = ENV.fetch('BMAKE', prefix + '/bin/bmake')
patch = File.expand_path('../patches/pkgsrc-cwrappers-unwrap-boundary.patch', __dir__)
contract = File.expand_path('cwrappers-unwrap.c', __dir__)
commands = []
hashes = [patch, contract, libtool, prefix + '/lib/libnbcompat.a'].to_h { |p| [p, Digest::SHA256.file(p).hexdigest] }
(Dir.glob(tree + '/pkgtools/cwrappers/**/*').select { |p| File.file?(p) } + [tree + '/mk/cwrappers.mk']).each do |p|
  hashes[p] = Digest::SHA256.file(p).hexdigest
end
hashes[cc.first] = Digest::SHA256.file(cc.first).hexdigest if File.file?(cc.first)
env = %w[CPATH C_INCLUDE_PATH CPLUS_INCLUDE_PATH LIBRARY_PATH GCC_EXEC_PREFIX COMPILER_PATH].to_h { |k| [k, nil] }
env['LC_ALL'] = 'C'
run = lambda do |name, argv, cwd = work, extra = {}, allowed = [0]|
  out, err, status = Open3.capture3(env.merge(extra), *argv, chdir: cwd)
  File.write(work + '/' + name + '.stdout', out)
  File.write(work + '/' + name + '.stderr', err)
  commands << { name: name, argv: argv, cwd: cwd, status: status.exitstatus }
  File.write(work + '/commands.json', JSON.pretty_generate(commands) + "\n")
  abort "Failed #{name}: #{err}" unless allowed.include?(status.exitstatus)
  [out, status.exitstatus]
end
abort 'Native GCC16.2.0 required' unless run.call('compiler-version', [*cc, '-dumpfullversion']).first.strip == '16.2.0'
run.call('compiler-machine', [*cc, '-dumpmachine'])
run.call('libtool-version', [libtool, '--version'])
flags = ['-D_GNU_SOURCE', '-DNEED_MI_VECTOR_HASH', '-I' + prefix + '/include']
variants = {}
%w[old new].each do |variant|
  root = work + '/' + variant
  FileUtils.mkdir_p(root + '/pkgtools')
  FileUtils.cp_r(tree + '/pkgtools/cwrappers', root + '/pkgtools')
  FileUtils.cp_r(tree + '/mk', root)
  Dir.children(tree).each do |name|
    File.symlink(tree + '/' + name, root + '/' + name) unless %w[mk pkgtools devel].include?(name)
  end
  Dir.children(tree + '/pkgtools').each do |name|
    File.symlink(tree + '/pkgtools/' + name, root + '/pkgtools/' + name) unless name == 'cwrappers'
  end
  FileUtils.mkdir_p(root + '/devel')
  FileUtils.cp_r(tree + '/devel/zlib', root + '/devel')
  Dir.children(tree + '/devel').each do |name|
    File.symlink(tree + '/devel/' + name, root + '/devel/' + name) unless name == 'zlib'
  end
  source = root + '/pkgtools/cwrappers/files/bin'
  prepared = File.read(source + '/fixup-libtool.c').include?('!isabs(line[r->src_len])')
  if variant == 'old' && prepared
    run.call('reverse-patch', ['patch', '-f', '-R', '-F', '0', '-p1', '-i', patch], root)
  elsif variant == 'new' && !prepared
    run.call('patch', ['patch', '-f', '-N', '-F', '0', '-p1', '-i', patch], root)
  end
  if ENV['NATIVE_MAKECONF']
    config = File.realpath(ENV.fetch('NATIVE_MAKECONF'))
    hashes[config] = Digest::SHA256.file(config).hexdigest
    values = run.call(variant + '-package-metadata', [make, 'MAKECONF=' + config,
      '-V', 'PKGNAME', '-V', '${PKG_FAIL_REASON}'], root + '/pkgtools/cwrappers').first.lines.map(&:chomp)
    expected = variant == 'old' ? 'cwrappers-20220403' : 'cwrappers-20220403nb1'
    abort 'Unexpected package metadata' unless values == [expected, '']
    depends = run.call(variant + '-consumer-metadata', [make, 'MAKECONF=' + config,
      '-V', '${TOOL_DEPENDS}'], root + '/devel/zlib').first.split.grep(/\Acwrappers/)
    expected = variant == 'old' ? '20150314' : '20220403nb1'
    abort 'Unexpected wrapper dependency' unless depends == ["cwrappers>=#{expected}:../../pkgtools/cwrappers"]
  end
  # Configure and build the upstream programs, not substitutes for the wrappers.
  run.call(variant + '-configure', ['sh', './configure'], source, 'CC' => Shellwords.join(cc))
  run.call(variant + '-build', [make, '-m', prefix + '/share/mk', 'CC=' + Shellwords.join(cc),
    'NEED_MI_VECTOR_HASH=1', 'CPPFLAGS=' + Shellwords.join(flags), 'CFLAGS=-O2 -g',
    'LDFLAGS=-L' + prefix + '/lib', 'all'], source)
  run.call(variant + '-contract-build', [*cc, '-O2', '-g', *flags, '-I' + source,
    contract, *%w[alloc.c common.c mi_vector_hash.c reorder-cc.c generic-transform-libtool.c normalise-cc.c cleanup-cc.c].map { |f| source + '/' + f },
    '-L' + prefix + '/lib', '-lnbcompat', '-o', root + '/contract'])
  variants[variant] = { root: root, source: source }
end
# Two genuine installed native DSOs distinguish a directory and its sibling.
%w[inside outside].each do |name|
  dir = work + '/' + name
  dest = work + '/sdk/runtime' + (name == 'outside' ? '-other' : '')
  FileUtils.mkdir_p(dir)
  FileUtils.mkdir_p(dest)
  File.write(dir + '/' + name + '.c', "int\n#{name}(void)\n{\n\treturn 1;\n}\n")
  run.call(name + '-compile', [libtool, '--tag=CC', '--mode=compile', *cc, '-g', '-O2', '-c', name + '.c', '-o', name + '.lo'], dir)
  run.call(name + '-link', [libtool, '--tag=CC', '--mode=link', *cc, '-shared', name + '.lo', '-o', 'lib' + name + '.la', '-rpath', dest, '-version-info', '0:0:0'], dir)
  run.call(name + '-install', [libtool, '--mode=install', 'install', '-c', 'lib' + name + '.la', dest], dir)
end
results = {}
variants.each do |variant, paths|
  dir = paths.fetch(:root) + '/consumer'
  FileUtils.mkdir_p(dir + '/config')
  FileUtils.mkdir_p(dir + '/installed')
  wrapper = paths.fetch(:source) + '/libtool-wrapper'
  File.write(dir + '/config/libtool', "exec=#{libtool}\nexec_path=#{wrapper}\nworklog=#{dir}/work.log\nunwrap=#{work}/sdk/runtime:/usr/pkg/gcc16\n")
  File.write(dir + '/probe.c', "extern int inside(void), outside(void);\nint\nvalue(void)\n{\n\treturn inside() + outside();\n}\n")
  extra = { 'CWRAPPERS_CONFIG_DIR' => dir + '/config' }
  run.call(variant + '-consumer-compile', [wrapper, '--tag=CC', '--mode=compile', *cc, '-g', '-c', 'probe.c', '-o', 'probe.lo'], dir, extra)
  run.call(variant + '-consumer-link', [wrapper, '--tag=CC', '--mode=link', *cc, '-shared', 'probe.lo',
    work + '/sdk/runtime/libinside.la', work + '/sdk/runtime-other/liboutside.la',
    '-o', 'libprobe.la', '-rpath', '/usr/pkg/lib', '-version-info', '0:0:0'], dir, extra)
  run.call(variant + '-consumer-install', [wrapper, '--mode=install', 'install', '-c', 'libprobe.la', dir + '/installed'], dir, extra)
  installed = File.read(dir + '/installed/libprobe.la')[/^dependency_libs='(.*)'$/, 1]
  abort 'Intended archive mapping lost' unless installed.include?('-L/usr/pkg/gcc16 -linside')
  expected = variant == 'old' ? '-L/usr/pkg/gcc16-other -loutside' : work + '/sdk/runtime-other/liboutside.la'
  abort 'Actual sibling regression not observed' unless installed.include?(expected)
  results[variant] = { installed_dependency_libs: installed,
    wrapper_sha256: Digest::SHA256.file(wrapper).hexdigest }
  # Exercise both .la basename branches and the existing -L boundary rules.
  fixture = paths.fetch(:root) + '/fixture'
  FileUtils.mkdir_p(fixture + '/.libs')
  terms = %w[/sdk/runtime/libexact.la /sdk/runtime/sub/libchild.la /sdk/runtime/plugin.la
    /sdk/runtime-other/libsibling.la /sdk/runtime-other/plugin.la
    -L/sdk/runtime -L/sdk/runtime/sub -L/sdk/runtime-other /sdk/r.la]
  archive = "dependency_libs='#{terms.join(' ')}'\n"
  %w[case.la .libs/case.lai].each { |p| File.write(fixture + '/' + p, archive) }
  run.call(variant + '-metadata', [paths.fetch(:root) + '/contract', '/sdk/runtime:/target', 'case.la'], fixture)
  actual = File.read(fixture + '/.libs/case.lai')[/^dependency_libs='(.*)'$/, 1].split
  expected_terms = %w[-L/target -lexact -L/target/sub -lchild /target/plugin.la]
  expected_terms += variant == 'old' ? %w[-L/target-other -lsibling /target-other/plugin.la] : %w[/sdk/runtime-other/libsibling.la /sdk/runtime-other/plugin.la]
  expected_terms += %w[-L/sdk/runtime-other /sdk/r.la]
  abort "Unexpected metadata: #{actual}" unless actual == expected_terms
  results[variant][:fixture_dependency_libs] = actual
  %w[case.la .libs/case.lai].each { |p| File.write(fixture + '/' + p, archive) }
  memlog = work + '/' + variant + '-memcheck.log'
  _, status = run.call(variant + '-memcheck', [ENV.fetch('VALGRIND', 'valgrind'), '--leak-check=full',
    '--show-leak-kinds=all', '--errors-for-leak-kinds=all', '--error-exitcode=99', '--log-file=' + memlog,
    paths.fetch(:root) + '/contract', '/sdk/runtime:/target', 'case.la'], fixture, {}, variant == 'old' ? [99] : [0])
  log = File.read(memlog)
  if variant == 'old'
    abort 'Original temporary-path leak not reproduced' unless log.include?('fixup_libtool_la') && log.include?('definitely lost: 33 bytes in 2 blocks')
  else
    abort 'Memory contract did not pass' unless log.include?('All heap blocks were freed') && log.include?('ERROR SUMMARY: 0 errors')
  end
  results[variant][:memcheck_status] = status
end
hashes.each { |p, sha| abort "Input changed: #{p}" unless Digest::SHA256.file(p).hexdigest == sha }
File.write(work + '/result.json', JSON.pretty_generate(inputs: hashes, results: results,
  scope: 'Native GCC16 upstream wrappers and genuine Libtool install; bounded module Memcheck, no target/package installation.') + "\n")
puts 'PASS: actual installed metadata preserves the sibling; both archive branches and temporary-path ownership checked'
