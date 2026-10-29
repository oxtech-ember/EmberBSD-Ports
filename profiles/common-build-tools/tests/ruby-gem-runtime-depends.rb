#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted); every runtime dependency of a gem is a DEPENDS or ships with Ruby.
require 'open3'
require 'rubygems/package'

usage = 'usage: ruby-gem-runtime-depends.rb EXPORTED_PKGSRC MAKECONF DISTDIR NEW_WORK (BMAKE, PKG_ADMIN)'
abort usage unless ARGV.length == 4 && ENV['BMAKE'] && ENV['PKG_ADMIN']
tree, makeconf, distdir = ARGV.take(3).map { |path| File.realpath(path) }
work = File.expand_path(ARGV[3])
abort 'NEW_WORK must be new' if File.exist?(work) || File.symlink?(work)
Dir.mkdir(work)

ROOTS = %w[net/ruby-train-winrm].freeze

def vars(tree, makeconf, pkgpath, *names)
  out, err, status = Open3.capture3({ 'MAKECONF' => makeconf }, ENV['BMAKE'],
                                    *names.flat_map { |name| ['-v', name] }, chdir: "#{tree}/#{pkgpath}")
  abort "#{pkgpath}: bmake failed: #{err}" unless status.success?
  names.zip(out.lines.map(&:strip)).to_h
end

# gem.mk installs the distfile's gemspec with OVERRIDE_GEMSPEC applied by update-gemspec.rb.
def gemspec(tree, distdir, work, v)
  spec = Gem::Package.new("#{distdir}/#{v['DISTFILES'].split.first}").spec
  file = "#{work}/#{spec.full_name}.gemspec"
  File.write(file, spec.to_ruby)
  unless v['OVERRIDE_GEMSPEC'].empty?
    out, status = Open3.capture2e(RbConfig.ruby, "#{tree}/lang/ruby/files/update-gemspec.rb", file,
                                  *v['OVERRIDE_GEMSPEC'].split)
    abort "#{file}: update-gemspec.rb failed:\n#{out}" unless status.success?
  end
  Gem::Specification.load(file)
end

# Default and bundled gems that come with the Ruby running this test.
shipped = (Dir["#{Gem.default_specifications_dir}/*.gemspec"] +
           Dir["#{Gem.default_dir}/specifications/*.gemspec"])
          .map { |file| Gem::Specification.load(file) }.group_by(&:name)

info = {}
load = lambda do |pkgpath|
  info[pkgpath] ||= begin
    v = vars(tree, makeconf, pkgpath, 'PKGNAME', 'PKG_FAIL_REASON', 'DEPENDS', 'DISTFILES', 'OVERRIDE_GEMSPEC')
    abort "#{pkgpath}: #{v['PKG_FAIL_REASON']}" unless v['PKG_FAIL_REASON'].empty?
    v.merge('spec' => gemspec(tree, distdir, work, v))
  end
end

direct = {}
errors = []
deps_of = lambda do |pkgpath|
  direct[pkgpath] ||= load.call(pkgpath)["DEPENDS"].split.filter_map do |dep|
    pattern, dir = dep.split(":")
    dep_path = dir.delete_prefix("../../")
    next unless File.basename(dep_path).start_with?("ruby-")
    target = load.call(dep_path)
    _, status = Open3.capture2e(ENV["PKG_ADMIN"], "pmatch", pattern, target["PKGNAME"])
    errors << "#{pkgpath}: #{pattern} rejects #{target["PKGNAME"]}" unless status.success?
    dep_path
  end
end
closure = lambda do |root|
  seen = []
  queue = deps_of.call(root).dup
  until queue.empty?
    pkgpath = queue.shift
    next if seen.include?(pkgpath)
    seen << pkgpath
    queue.concat(deps_of.call(pkgpath))
  end
  seen
end

done = ROOTS.flat_map { |root| [root] + closure.call(root) }.uniq
done.each do |pkgpath|
  # A dependency installed through another DEPENDS is installed as well.
  provided = closure.call(pkgpath).to_h { |path| [load.call(path)["spec"].name, [path, load.call(path)["spec"].version]] }
  spec = load.call(pkgpath)["spec"]
  spec.runtime_dependencies.each do |dep|
    if (path, version = provided[dep.name])
      errors << "#{pkgpath}: #{dep.name} #{dep.requirement} rejects #{path} #{version}" unless dep.match?(dep.name, version)
    elsif (shipped[dep.name] || []).none? { |s| dep.match?(s) }
      errors << "#{pkgpath}: gem #{spec.full_name} needs #{dep.name} #{dep.requirement}, " \
                "which is neither in its DEPENDS nor shipped with Ruby"
    end
  end
end
abort errors.join("\n") unless errors.empty?
puts "PASS: #{done.size} gem packages under #{ROOTS.join(', ')} depend on every runtime dependency of their gemspec"
