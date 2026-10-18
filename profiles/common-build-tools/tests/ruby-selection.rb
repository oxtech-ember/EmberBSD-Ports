#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted); real pkgsrc Ruby provider selection.
require 'fileutils'
require 'json'
require 'open3'
abort 'Usage: ruby-selection.rb EXPORTED_PKGSRC NATIVE_MAKECONF CROSS_MAKECONF NEW_WORK' unless ARGV.size == 4
tree, native_conf, cross_conf = ARGV.take(3).map { |p| File.realpath(p) }
work = File.expand_path(ARGV[3])
abort 'Output exists.' if File.exist?(work) || File.symlink?(work)
FileUtils.mkdir_p(work)
root = File.expand_path('../../..', __dir__)
profiles = {
  'native' => root + '/profiles/common-build-tools/mk.conf',
  'cross' => root + '/profiles/common-build-tools/cross/mk.conf'
}
block = /^# (?:Use the current canonical Ruby provider for build generators and packages\.|This also selects native Ruby for recursive host generator dependencies\.)\nRUBY_VERSION_DEFAULT= 40\n\.if \$\{RUBY_VERSION_DEFAULT\} != "40"\nPKG_FAIL_REASON\+= "The common tools (?:cross )?profile requires the current Ruby 4\.0 provider"\n\.endif\n/
sources = {}
profiles.each do |kind, path|
  text = File.read(path)
  abort 'Expected one scoped Ruby selection.' unless text.scan(block).size == 1
  sources[kind] = { 'before' => text.sub(block, ''), 'fixed' => text }
end
FileUtils.cp(root + '/profiles/common-build-tools/cross/sort-c.sh', work)
configs = {}
%w[before fixed].each do |revision|
  profiles.each_key do |kind|
    path = work + '/' + revision + '-' + kind + '.mk'
    File.write(path, sources.fetch(kind).fetch(revision))
    text = File.read(kind == 'native' ? native_conf : cross_conf)
    # Private build selections must not hide the source profile's choice.
    text = text.gsub(/^RUBY_VERSION_DEFAULT\s*[?:+]?=.*\n/, '')
    pattern = /^\.include "[^"\n]*(?:\/profiles\/common-build-tools\/cross\/mk\.conf|\/EMBERBSD-CROSS-MK\.CONF)"$/
    if kind == 'cross'
      abort 'Expected one cross-profile include.' unless text.scan(pattern).size == 1
      text = text.sub(pattern, '.include "' + path + '"')
    else
      text += "\n.include \"#{path}\"\n"
    end
    configs[revision + '-' + kind] = work + '/' + revision + '-' + kind + '.conf'
    File.write(configs.fetch(revision + '-' + kind), text)
  end
end
plain = File.read(native_conf).gsub(/^RUBY_VERSION_DEFAULT\s*[?:+]?=.*\n/, '')
File.write(work + '/unrelated.conf', plain)
keys = %w[RUBY_VERSION_DEFAULT RUBY_VER RUBY_VERSION RUBY_PKGPREFIX PKGNAME RUBY USE_CROSS_COMPILE CC CXX CMAKE_CONFIGURE_ARGS PKG_FAIL_REASON]
commands = []
query = lambda do |name, conf, extra = []|
  argv = [ENV.fetch('BMAKE', 'bmake'), '-C', tree + '/textproc/ruby-asciidoctor',
          'MAKECONF=' + conf, 'WRKOBJDIR=' + work + '/objects', 'PACKAGES=' + work + '/packages',
          '_PKGSRC_BARRIER=yes', *extra, *keys.flat_map { |key| ['-V', '${' + key + '}'] }]
  stdout, stderr, status = Open3.capture3({ 'LC_ALL' => 'C' }, *argv)
  File.write(work + '/' + name + '.stdout', stdout)
  File.write(work + '/' + name + '.stderr', stderr)
  commands << { name: name, argv: argv, status: status.exitstatus }
  File.write(work + '/commands.json', JSON.pretty_generate(commands) + "\n")
  abort 'Failed metadata query: ' + name unless status.success?
  lines = stdout.lines(chomp: true)
  abort 'Wrong metadata shape: ' + name unless lines.size == keys.size
  keys.zip(lines).to_h
end
results = {}
%w[before fixed].each do |revision|
  {
    'native' => ['native', []],
    'aarch64' => ['cross', ['EMBERBSD_CROSS_TARGET=aarch64']],
    'amd64' => ['cross', ['EMBERBSD_CROSS_TARGET=amd64']],
    'host-recursion' => ['cross', ['USE_CROSS_COMPILE=no']]
  }.each do |kind, (profile, extra)|
    name = revision + '-' + kind
    data = query.call(name, configs.fetch(revision + '-' + profile), extra)
    expected = revision == 'fixed' ? '40' : '34'
    abort 'Wrong selected provider: ' + name unless data['RUBY_VERSION_DEFAULT'] == expected && data['RUBY_VER'] == expected && data['RUBY_PKGPREFIX'] == 'ruby' + expected && data['PKGNAME'] == 'ruby' + expected + '-asciidoctor-2.0.26'
    abort 'Wrong current Ruby source.' if revision == 'fixed' && data['RUBY_VERSION'] != '4.0.7'
    if kind == 'host-recursion'
      abort 'Host Ruby was forced cross.' unless data['USE_CROSS_COMPILE'] == 'no' && !data['CMAKE_CONFIGURE_ARGS'].include?('-DCMAKE_SYSTEM_NAME')
    end
    results[name] = data
  end
end
%w[native aarch64 amd64 host-recursion].each do |kind|
  a = results.fetch('before-' + kind)
  b = results.fetch('fixed-' + kind)
  abort 'Unrelated compiler, cross mode or existing guards changed.' unless %w[USE_CROSS_COMPILE CC CXX CMAKE_CONFIGURE_ARGS PKG_FAIL_REASON].all? { |key| a[key] == b[key] }
end
unrelated = query.call('unrelated', work + '/unrelated.conf')
abort 'Unrelated default changed.' unless unrelated['RUBY_VERSION_DEFAULT'] == '34' && unrelated['PKGNAME'].start_with?('ruby34-')
%w[native cross].each do |kind|
  data = query.call('override-' + kind, configs.fetch('fixed-' + kind), ['RUBY_VERSION_DEFAULT=34'])
  abort 'Obsolete override was not rejected.' unless data['PKG_FAIL_REASON'].include?('requires the current Ruby 4.0 provider')
end
native_cross = query.call('native-cross-rejected', configs.fetch('fixed-native'), ['USE_CROSS_COMPILE=yes'])
abort 'Native-only barrier changed.' unless native_cross['PKG_FAIL_REASON'].include?('require native package builds')
File.write(work + '/result.json', JSON.pretty_generate({
  scope: 'Actual pkgsrc metadata for native/common cross/host recursion; no Ruby build or target execution.',
  results: results, unrelated: unrelated
}) + "\n")
puts 'PASS: current Ruby 4.0.7 provider, Asciidoctor40, native host routing, existing barriers and unrelated default.'
