#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted); actual pkgsrc bootstrap dependency metadata.
require 'fileutils'
require 'json'
require 'open3'
abort 'Usage: bsdtar-common-zlib.rb EXPORTED_PKGSRC NATIVE_MAKECONF CROSS_MAKECONF NEW_WORK' unless ARGV.size == 4
tree, native, cross = ARGV.take(3).map { |p| File.realpath(p) }
out = File.expand_path(ARGV[3])
abort 'Output exists.' if File.exist?(out) || File.symlink?(out)
FileUtils.mkdir_p(out)
configs = {}
{ 'native' => native, 'cross' => cross }.each do |kind, path|
  configs[kind] = out + '/' + kind + '.conf'
  File.write(configs[kind], File.read(path).gsub(/^EMBERBSD_BSDTAR_USE_COMMON_ZLIB\s*[?:+]?=.*\n/, ''))
end
keys = %w[PKGNAME DEPENDS CPPFLAGS LDFLAGS WRKDIR CC CXX USE_CROSS_COMPILE USE_BUILTIN.zlib EMBERBSD_BSDTAR_USE_COMMON_ZLIB]
commands = []
query = lambda do |name, config, extra|
  argv = [ENV.fetch('BMAKE', 'bmake'), '-C', tree + '/archivers/bsdtar',
          'MAKECONF=' + configs.fetch(config), 'WRKOBJDIR=' + out + '/objects',
          'PACKAGES=' + out + '/packages', '_PKGSRC_BARRIER=yes', *extra,
          *keys.flat_map { |key| ['-V', '${' + key + '}'] }]
  stdout, stderr, status = Open3.capture3({ 'LC_ALL' => 'C' }, *argv)
  File.write(out + '/' + name + '.stdout', stdout)
  File.write(out + '/' + name + '.stderr', stderr)
  commands << { name: name, argv: argv, status: status.exitstatus }
  File.write(out + '/commands.json', JSON.pretty_generate(commands) + "\n")
  abort 'Metadata query failed: ' + name unless status.success?
  abort 'Unexpected metadata shape.' unless stdout.lines.size == keys.size
  keys.zip(stdout.lines(chomp: true)).to_h
end
results = {}
results['bootstrap'] = query.call('bootstrap', 'native', ['EMBERBSD_BSDTAR_USE_COMMON_ZLIB=no'])
before = results.fetch('bootstrap')
abort 'Original bootstrap metadata changed.' unless before['PKGNAME'] == 'bsdtar-3.8.9' && !before['DEPENDS'].include?('zlib>=') && before['CPPFLAGS'].include?(before['WRKDIR'] + '/zlib') && before['LDFLAGS'].include?(before['WRKDIR'] + '/zlib')
{
  'native-opt-in' => ['native', ['EMBERBSD_BSDTAR_USE_COMMON_ZLIB=yes']],
  'native-common' => ['native', ['EMBERBSD_COMMON_TOOLS=yes']],
  'target' => ['cross', []],
  'host-recursion' => ['cross', ['USE_CROSS_COMPILE=no']]
}.each do |name, (config, extra)|
  row = query.call(name, config, extra)
  abort 'Current zlib package was not selected: ' + name unless row['PKGNAME'] == 'bsdtar-3.8.9nb1' && row['DEPENDS'].include?('zlib>=1.3.2nb1') && row['USE_BUILTIN.zlib'] == 'no'
  abort 'Copied-source flags remain: ' + name if %w[CPPFLAGS LDFLAGS].any? { |key| row[key].include?(row['WRKDIR'] + '/zlib') }
  results[name] = row
end
abort 'Native compiler routing changed.' unless %w[CC CXX USE_CROSS_COMPILE].all? { |key| results['native-opt-in'][key] == before[key] }
abort 'Common default differs from explicit opt-in.' unless results['native-common'] == results['native-opt-in']
abort 'Target compiler was lost.' unless results['target']['USE_CROSS_COMPILE'].downcase == 'yes' && results['target']['CC'].include?('aarch64--netbsd-gcc')
abort 'Host tool was forced cross.' unless results['host-recursion']['USE_CROSS_COMPILE'].downcase == 'no' && !results['host-recursion']['CC'].include?('aarch64--netbsd-')
File.write(out + '/result.json', JSON.pretty_generate({ scope: 'Actual pkgsrc dependency and compiler metadata; no build or target execution.', results: results }) + "\n")
puts 'PASS: current registered-package dependency, original bootstrap route, native compiler identity and cross host recursion.'
