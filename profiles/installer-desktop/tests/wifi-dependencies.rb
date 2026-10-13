# Origin: EmberBSD native Wi-Fi package dependency regression, prepared with AI assistance.
# SPDX-License-Identifier: BSD-2-Clause
require 'open3'
require 'tmpdir'
abort 'Usage: ruby wifi-dependencies.rb package-directory target-readelf' unless ARGV.size == 2
directory, readelf = ARGV
packages = {}
providers = Hash.new { |h, k| h[k] = [] }
Dir.glob(File.join(directory, '*.tgz')).each do |archive|
  contents, error, status = Open3.capture3('tar', '-xOf', archive, '+CONTENTS')
  abort error unless status.success?
  name = contents[/^@name (.+)$/, 1] or abort "No package name: #{archive}"
  packages[name] = {archive: archive, depends: contents.scan(/^@pkgdep (.+)$/).flatten}
  contents.each_line do |line|
    file = line.strip
    providers[File.basename(file)] << name if file.match?(%r{\Alib/[^\s]+\.so(?:\.[0-9]+)*\z})
  end
end
leaf = packages.keys.find { |name| name.start_with?('dhcpcd-gtk3-') } or abort 'Missing Wi-Fi leaf'
closure = []
pending = [leaf]
until pending.empty?
  name = pending.shift
  next if closure.include?(name)
  closure << name
  packages.fetch(name)[:depends].each do |pattern|
    prefix = pattern.split(/>=|<=|==|>|</, 2).first
    matches = packages.keys.select do |candidate|
      pattern.include?('[') ? File.fnmatch?(pattern, candidate) : candidate.match?(/\A#{Regexp.escape(prefix)}-[0-9]/)
    end
    abort "Ambiguous or missing dependency: #{pattern}" unless matches.size == 1
    pending << matches.first
  end
end
Dir.mktmpdir do |temporary|
  binary, error, status = Open3.capture3('tar', '-xOf', packages.fetch(leaf)[:archive], 'bin/dhcpcd-gtk')
  abort error unless status.success?
  path = File.join(temporary, 'dhcpcd-gtk')
  File.binwrite(path, binary)
  dynamic, error, status = Open3.capture3(readelf, '-d', path)
  abort error unless status.success?
  dynamic.scan(/\(NEEDED\).*?\[([^\]]+)\]/).flatten.each do |library|
    owners = providers[library]
    # Libraries in the base/X11 sets are outside this package closure.
    next if owners.empty?
    abort "Undeclared runtime dependency: #{library} (#{owners.join(', ')})" if (owners & closure).empty?
  end
end
puts 'Wi-Fi ELF package libraries are provided by its declared native package closure'
