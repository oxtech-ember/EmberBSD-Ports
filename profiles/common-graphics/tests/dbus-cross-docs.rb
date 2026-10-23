#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), actual D-Bus host XSLT/catalog regression.
require 'digest'
require 'fileutils'
require 'open3'
require 'shellwords'

abort 'usage: dbus-cross-docs.rb PKGSRC CROSS_MAKECONF BUILT_SOURCE NEW_WORK' unless ARGV.length == 4
tree, conf, source = ARGV.first(3).map { |p| File.realpath(p) }
work = File.expand_path(ARGV.last)
abort 'NEW_WORK must be new and absolute' unless ARGV.last.start_with?('/') && !File.exist?(work)
make = ENV.fetch('BMAKE', 'bmake')
meson = ENV.fetch('MESON', 'meson')
recipe = File.expand_path('../../../pkgsrc/sysutils/dbus', __dir__)
stock = File.expand_path('../../../upstream/pkgsrc/sysutils/dbus', __dir__)
wrkdir = File.dirname(source)
wrktop = File.expand_path('../../../..', source)
FileUtils.mkdir_p(work)
inputs = [__FILE__, conf, "#{source}/meson.build", "#{wrkdir}/.meson_cross",
          "#{source}/output/doc/dbus-send.1.xml"]

%w[original patched].each do |variant|
  root = "#{work}/#{variant}"
  FileUtils.mkdir_p("#{root}/sysutils")
  Dir.children(tree).each do |entry|
    next if entry == 'sysutils'
    FileUtils.ln_s("#{tree}/#{entry}", "#{root}/#{entry}")
  end
  Dir.children("#{tree}/sysutils").each do |entry|
    next if entry == 'dbus'
    FileUtils.ln_s("#{tree}/sysutils/#{entry}", "#{root}/sysutils/#{entry}")
  end
  origin = variant == 'original' ? stock : recipe
  FileUtils.cp_r(origin, "#{root}/sysutils/dbus")
  inputs << "#{origin}/Makefile"
end
query = lambda do |variant, native|
  out, status = Open3.capture2e(make, '-C', "#{work}/#{variant}/sysutils/dbus",
    "MAKECONF=#{conf}", "WRKOBJDIR=#{wrktop}",
    *Array(native ? 'USE_CROSS_COMPILE=no' : nil), '-V',
    '${OPSYS}|${MESON_BINARY.xsltproc:U}|${MESON_ARGS}')
  File.write("#{work}/#{variant}-#{native ? 'native' : 'cross'}.log", out)
  abort 'recipe parsing failed' unless status.success?
  out.strip
end
old = query.call('original', false).split('|', 3)
new = query.call('patched', false).split('|', 3)
abort 'unexpected target metadata' unless old[0] == 'NetBSD' && new[0] == 'NetBSD'
abort 'original recipe already selects xsltproc' unless old[1].empty?
xsltproc = new[1]
abort 'corrected native tool is not an absolute executable' unless xsltproc.start_with?('/') && File.executable?(xsltproc)
abort 'docs are not required' unless Shellwords.split(new[2]).include?('-Dxml_docs=enabled')
abort 'native recipe behavior changed' unless query.call('original', true) == query.call('patched', true)
puts 'GREEN: real recipe selects the native XSLT tool and requires docs only for cross builds'

body = File.read("#{source}/meson.build")[/^xsltproc = find_program\('xsltproc'.*?^# For doxygen/m]
abort 'upstream documentation probe changed' unless body
body = body.sub(/^# For doxygen\z/, '')
fixture = "#{work}/source"
FileUtils.mkdir_p(fixture)
File.write("#{fixture}/meson.build", "project('dbus-cross-docs')\n" + body +
  "\nif not build_xml_docs\n  error('DBUS_REQUIRED_DOCS_MISSING')\nendif\n")
File.write("#{fixture}/meson_options.txt", "option('xml_docs', type: 'feature', value: 'auto')\n")
FileUtils.cp("#{source}/output/doc/dbus-send.1.xml", "#{work}/dbus-send.1.xml")
base_cross = File.read("#{wrkdir}/.meson_cross")
abort 'original machine file already selects xsltproc' if base_cross.match?(/^xsltproc\s*=/)
%w[original patched missing-tool].each do |variant|
  cross = base_cross.dup
  args = []
  unless variant == 'original'
    selected = variant == 'patched' ? xsltproc : "#{work}/absent-xsltproc"
    cross.sub!("[binaries]\n", "[binaries]\nxsltproc = '#{selected}'\n") or abort 'missing binaries section'
    args << '-Dxml_docs=enabled'
  end
  File.write("#{work}/#{variant}.cross", cross)
  out, status = Open3.capture2e({ 'PATH' => '/usr/bin:/bin' }, meson, 'setup',
    "#{work}/build-#{variant}", fixture, '--cross-file', "#{work}/#{variant}.cross",
    *args)
  File.write("#{work}/#{variant}-configure.log", "exit=#{status.exitstatus}\n#{out}")
  if variant == 'original'
    abort 'original catalog failure not reproduced' unless !status.success? &&
      out.include?('/usr/bin/xsltproc') && out.include?('DBUS_REQUIRED_DOCS_MISSING') &&
      out.include?('Docbook XSL "html" not found')
    puts 'RED: actual upstream probe with platform xsltproc cannot resolve the installed catalog'
  elsif variant == 'patched'
    abort 'selected native catalog probe failed' unless status.success?
    puts 'GREEN: actual upstream HTML and manpage stylesheet probes pass with the selected native tool'
  else
    abort 'missing native tool did not fail configuration' if status.success?
    puts 'GREEN: absent required native XSLT tool is rejected during configuration'
  end
end
%w[html manpages].each do |format|
  output = "#{work}/dbus-send.#{format == 'html' ? 'html' : '1'}"
  out, status = Open3.capture2e(xsltproc, '--nonet', '--xinclude', '-o', output,
    "http://docbook.sourceforge.net/release/xsl/current/#{format}/docbook.xsl",
    "#{work}/dbus-send.1.xml")
  File.write("#{work}/transform-#{format}.log", "exit=#{status.exitstatus}\n#{out}")
  abort 'real document transform failed' unless status.success? && File.size?(output)
  abort 'missing document content' unless File.read(output).include?('dbus-send')
  inputs << output
end
inputs << xsltproc
File.write("#{work}/inputs.sha256", inputs.uniq.map { |p| "#{Digest::SHA256.file(p).hexdigest}  #{p}\n" }.join)
puts 'PASS: real D-Bus XML produces HTML and a manpage; target D-Bus runtime remains separate acceptance'
