#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Exercise the real pkgsrc libtool PLIST helper.
require 'fileutils'
require 'open3'
require 'shellwords'
abort 'Usage: cross-sort.rb PACKAGE_DIRECTORY MAKECONF NEW_OUTPUT' unless ARGV.length == 3
package, config, output = ARGV.map { |path| File.expand_path(path) }
Dir.mkdir(output)
make = ENV.fetch('BMAKE', 'bmake')
query = [make, '-C', package, "MAKECONF=#{config}"]
def run!(*command, **options)
  out, err, status = Open3.capture3(*command, **options)
  raise "Failed #{command.inspect}\n#{out}#{err}" unless status.success?
  out
end
begin
  makefiles = run!(*query, '-V', '${.MAKE.MAKEFILES}').split
  vars = makefiles.select { |file| File.file?(file) }.flat_map do |file|
    File.read(file).scan(/^\s*(TOOLS_PLATFORM\.[a-zA-Z0-9_.+-]+)\s*[?:+!]?=/).flatten
  end.uniq.sort
  values = run!(*query, *vars.flat_map { |var| ['-V', "${#{var}}"] }).lines.map(&:chomp)
  File.write(File.join(output, 'platform-tools.txt'), vars.zip(values).map { |name, value| "#{name}=#{value}" }.join("\n") + "\n")
  helper = run!(*query, '-V', '${_LIBTOOL_EXPAND}').strip
  sort = run!(*query, '-V', '${TOOLS_SORT}').strip
  File.write(File.join(output, 'commands.txt'), "#{helper}\nTOOLS_SORT=#{sort}\n")
  files = %w[lib/libfixture.a lib/libfixture.so lib/libfixture.so.1 lib/libfixture.so.1.0]
  FileUtils.mkdir_p(File.join(output, 'lib'))
  files.each { |file| File.write(File.join(output, file), "fixture\n") }
  File.write(File.join(output, 'lib/libfixture.la'), <<~LA)
    # libfixture.la - a libtool library file
    dlname='libfixture.so.1'
    library_names='libfixture.so.1.0 libfixture.so.1 libfixture.so'
    old_library='libfixture.a'
    installed=yes
  LA
  actual, error, status = Open3.capture3(*Shellwords.split(helper), 'lib/libfixture.la', chdir: output)
  File.write(File.join(output, 'libtool-expand.log'), actual + error)
  raise 'libtool-expand lost the packaged library files' unless status.success? && actual.lines.map(&:chomp) == files.sort
  raise "TOOLS_SORT is not one executable: #{sort}" unless sort.start_with?('/') && File.executable?(sort)
  input = File.join(output, 'input with spaces')
  sorted = File.join(output, 'output with spaces')
  lines = ["z", "a", "Z", "A", "a", "é"]
  File.write(input, lines.join("\n") + "\n")
  run!({ 'LC_ALL' => 'en_US.UTF-8' }, sort, '-u', '-o', sorted, input)
  raise 'Sort lost C collation or arguments' unless File.readlines(sorted, chomp: true) == lines.uniq.sort
  puts 'PASS: pkgsrc libtool PLIST expansion, C collation and sort argument forwarding'
rescue StandardError => error
  warn error.message
  exit 1
end
