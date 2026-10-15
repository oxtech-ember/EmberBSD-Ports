#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted).
require 'digest'
require 'open3'
abort "Usage: #{$PROGRAM_NAME} PKGSRC PAQT_PREFIX PA_PREFIX DISTFILES PACKAGES" unless ARGV.length == 5
pkgsrc, paqt, pa, distfiles, packages = ARGV.map { |p| File.expand_path(p) }
toolkit = File.expand_path('../..', __dir__)
def check(condition, message)
  abort "FAIL: #{message}" unless condition
end
def capture(*args)
  text, status = Open3.capture2e(*args)
  check(status.success?, "#{args.first}: #{text}")
  text
end
# Inspect the real consumer, not a copied QML import list.
record = File.readlines("#{toolkit}/sources.tsv").map { |line| line.chomp.split("\t") }
record = record.find { |row| row[0] == 'x11/plasma6-plasma-workspace' }
check(record, 'Workspace source manifest is missing')
archive = "#{distfiles}/#{record[1]}"
check(Digest::SHA256.file(archive).hexdigest == record[2], 'Workspace archive checksum differs')
consumer = capture('tar', '-xOf', archive,
  'plasma-workspace-6.8.0/applets/notifications/global/PulseAudio.qml')
check(consumer.match?(/^import org\.kde\.plasma\.private\.volume\b/), 'Expected notifications volume import is missing')
bmake = ENV.fetch('BMAKE', 'bmake')
depends = capture(bmake, '-C', "#{pkgsrc}/x11/plasma6-plasma-workspace", '-V', '${DEPENDS}')
check(depends.split.any? { |d| d.match?(/^plasma6-plasma-pa>=6\.8\.0:..\/..\/audio\/plasma6-plasma-pa$/) },
  'Workspace has no runtime provider for its volume QML import')
reverse = capture(bmake, '-C', "#{pkgsrc}/audio/plasma6-plasma-pa", '-V', '${DEPENDS}')
check(!reverse.include?(':../../x11/plasma6-plasma-workspace'), 'Volume dependency creates a Workspace cycle')
# A stale pkgsrc +CONTENTS must not produce a metadata-only archive.
{'pulseaudio-qt' => 'pulseaudio-qt-1.9.0',
 'plasma6-plasma-pa' => 'plasma6-plasma-pa-6.8.0'}.each do |recipe, package|
  plist = File.readlines("#{pkgsrc}/audio/#{recipe}/PLIST", chomp: true)
  expected = plist.reject { |line| line.empty? || line.start_with?('@') }.sort
  archived = capture('tar', '-tzf', "#{packages}/#{package}.tgz").lines.map(&:chomp)
  archived.reject! { |line| line.start_with?('+') || line.end_with?('/') }
  check(!expected.empty? && archived.sort == expected, "#{package} archive payload differs from PLIST")
end
# Resolve the installed pkg-config variable and require its advertised headers.
pc = File.read("#{paqt}/lib/pkgconfig/KF6PulseAudioQt.pc")
vars = pc.lines.map { |l| l.match(/^([A-Za-z_]+)=(.*)$/)&.captures }.compact.to_h
4.times { vars.transform_values! { |v| v.gsub(/\$\{([^}]+)\}/) { vars.fetch(Regexp.last_match(1), Regexp.last_match(0)) } } }
include_dir = vars.fetch('includedir').sub(%r{/+$}, '')
check(include_dir == '/usr/pkg/include/KF6/KF6PulseAudioQt', 'PulseAudioQt advertises the wrong include directory')
check(File.file?("#{paqt}#{include_dir.delete_prefix('/usr/pkg')}/PulseAudioQt/Context"), 'Advertised Context header is absent')
check(!pc.include?('-I/KF6PulseAudioQt'), 'Stale KF5 include path is present')
# Inspect the staged module and target plugin. This does not execute target QML.
module_dir = "#{pa}/qt6/qml/org/kde/plasma/private/volume"
qmldir = File.read("#{module_dir}/qmldir")
check(qmldir.match?(/^module org\.kde\.plasma\.private\.volume$/), 'Volume module identity differs')
plugin = qmldir[/^(?:optional )?plugin ([A-Za-z0-9_-]+)(?:\s|$)/, 1]
check(plugin, 'Volume plugin entry is missing')
check(File.file?("#{module_dir}/lib#{plugin}.so"), 'Volume plugin file is missing')
elf = File.binread("#{module_dir}/lib#{plugin}.so", 20)
check(elf.start_with?("\x7fELF") && elf.getbyte(4) == 2 && elf.getbyte(5) == 1 && elf[18, 2].unpack1('v') == 183,
  'Volume plugin is not little-endian ELF64 AArch64')
puts 'PASS: real notifications import, runtime dependency, no cycle, installed headers, QML module and target ELF'
