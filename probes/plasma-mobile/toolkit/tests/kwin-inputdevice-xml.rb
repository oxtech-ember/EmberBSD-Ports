#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Check the real KWin input XML and Qt marshalling.
require 'digest'
require 'fileutils'
require 'json'
require 'open3'
require 'rexml/document'

abort 'Usage: kwin-inputdevice-xml.rb HOST_QT KWIN_SOURCE TARGET_QT_SOURCE NEW_OUTPUT' unless ARGV.length == 4
qt, kwin, target_qt, work = ARGV.map { |path| File.expand_path(path) }
Dir.mkdir(work)

def run!(*command)
  output, error, status = Open3.capture3(*command)
  raise "Command failed: #{command.inspect}\n#{output}#{error}" unless status.success?
  [output, error]
end

def interface(bytes)
  doc = REXML::Document.new(bytes)
  result = {}
  REXML::XPath.each(doc, '/node/interface/property') do |property|
    name = property.attributes['name']
    raise "Duplicate property #{name}" if result.key?(name)
    result[name] = [property.attributes['type'], property.attributes['access']]
  end
  raise 'No input device properties' if result.empty?
  result
end

expected = { 'size' => ['(dd)', 'read'], 'defaultOutputArea' => ['(dddd)', 'read'],
             'outputArea' => ['(dddd)', 'readwrite'], 'defaultInputArea' => ['(dddd)', 'read'],
             'inputArea' => ['(dddd)', 'readwrite'], 'numModes' => ['au', 'read'],
             'currentModes' => ['au', 'read'] }
cache = File.read(File.join(qt, 'CMakeCache.txt'))
raise 'Native QtDBus must link its native libdbus directly' unless cache.include?("FEATURE_dbus_linked:BOOL=ON\n") && cache.include?("QT_FEATURE_dbus_linked:INTERNAL=ON\n")
raise 'Native generator regression currently requires a macOS framework build' unless RUBY_PLATFORM.include?('darwin')
source_qt = cache.lines.grep(/^CMAKE_HOME_DIRECTORY:INTERNAL=/).first.to_s.split('=', 2).last.to_s.strip
raise 'Cannot identify native Qt source' if source_qt.empty?
source_files = %w[qdbusargument.cpp qdbusargument.h qdbusmetatype.cpp qdbusmetatype.h]
source_files.each do |file|
  native = File.join(source_qt, 'src/dbus', file)
  target = File.join(target_qt, 'src/dbus', file)
  raise "Target marshaller differs: #{file}" unless FileUtils.compare_file(native, target)
end
File.write(File.join(work, 'marshaller-sources.sha256'), source_files.map do |file|
  "#{Digest::SHA256.file(File.join(target_qt, 'src/dbus', file)).hexdigest}  src/dbus/#{file}\n"
end.join)
target_cache = File.read(File.join(target_qt, 'CMakeCache.txt'))
raise 'Target QtDBus direct-link feature is not confirmed' unless target_cache.include?("FEATURE_dbus_linked:BOOL=ON\n")
xml = File.join(work, 'org.kde.kwin.InputDevice.xml')
stdout, stderr = run!(File.join(qt, 'bin/qdbuscpp2xml'), '-A', File.join(kwin, 'src/backends/libinput/device.h'), '-o', xml)
File.write(File.join(work, 'qdbuscpp2xml.log'), stdout + stderr)
properties = interface(File.read(xml))
raise 'Generated XML has an empty D-Bus signature' if properties.values.any? { |type, _access| type.to_s.empty? }
expected.each do |name, contract|
  raise "Changed wire contract for #{name}: #{properties[name].inspect}" unless properties[name] == contract
end
if ENV['BASELINE_XML']
  previous = interface(File.read(ENV.fetch('BASELINE_XML')))
  raise 'Generation removed or added properties' unless properties.keys.sort == previous.keys.sort
  properties.each do |name, contract|
    next if expected.key?(name)
    raise "Unrelated property changed: #{name}" unless previous[name] == contract
  end
  expected.each_key { |name| raise "Baseline does not reproduce empty signature #{name}" unless previous[name][0] == '' }
end
proxy = File.join(work, 'inputdevice')
run!(File.join(qt, 'bin/qdbusxml2cpp'), '-p', proxy, xml)
# The real XML-to-C++ consumer must continue to reject an empty signature.
bad_xml = File.join(work, 'invalid.xml')
File.write(bad_xml, File.read(xml).sub('type="(dd)"', 'type=""'))
output, error, status = Open3.capture3(File.join(qt, 'bin/qdbusxml2cpp'), '-p', File.join(work, 'invalid'), bad_xml)
File.write(File.join(work, 'invalid.log'), output + error)
raise 'Invalid XML signature was accepted' if status.success?
compiler = ENV.fetch('HOST_CXX', '/usr/bin/c++')
source = File.join(__dir__, 'kwin-inputdevice-xml.cpp')
flags = ['-std=c++20', "-F#{qt}/lib", "-I#{qt}/include"]
command = [compiler, *flags, source, '-framework', 'QtCore', '-framework', 'QtDBus', "-Wl,-rpath,#{qt}/lib", '-o', File.join(work, 'marshaller')]
File.write(File.join(work, 'compile_commands.json'), JSON.pretty_generate([{ directory: work, file: source, arguments: command }]))
output, error = run!(*command)
File.write(File.join(work, 'compile.log'), output + error)
output, error = run!(File.join(work, 'marshaller'))
File.write(File.join(work, 'marshaller.log'), output + error)
puts output
puts "PASS: #{properties.length} KWin properties; seven complex signatures; invalid-signature rejection; native/target marshaller source parity"
