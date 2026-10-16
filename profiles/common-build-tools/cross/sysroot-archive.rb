# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
require 'digest'
require 'fileutils'
require 'open3'
require 'pathname'
require 'rubygems/package'

module EmberSysrootArchive
  class Error < StandardError; end
  class ForwardReader
    def initialize(io)
      @io, @position = io, 0
    end
    def pos
      @position
    end
    def read(*args)
      value = @io.read(*args)
      @position += value.bytesize if value
      value
    end
    def eof?
      @io.eof?
    end
  end

  def self.extract(archives, root)
    raise Error, 'Use a fresh extraction directory' if File.exist?(root)
    Dir.mkdir(root)
    root = File.realpath(root)
    links, inventory = {}, {}
    inside = ->(path) { path.start_with?(root + '/') }
    member_path = lambda do |name|
      name = name.delete_prefix('./').delete_suffix('/')
      return root if name.empty? || name == '.'
      raise Error, 'Unsafe archive member' if name.start_with?('/') || name.split('/').any? { |part| part.empty? || %w[. ..].include?(part) }
      path = root + '/' + name
      raise Error, 'Archive path escapes sysroot' unless inside.call(path)
      path
    end
    archives.each do |archive|
      Open3.popen3('xz', '-dc', archive) do |input, output, error, thread|
        input.close
        Gem::Package::TarReader.new(ForwardReader.new(output)) do |tar|
          tar.each do |entry|
            path = member_path.call(entry.full_name)
            if path == root
              raise Error, 'Archive root must be a directory' unless entry.header.typeflag == '5'
              next
            end
            relative = path.delete_prefix(root + '/')
            kind, mode = entry.header.typeflag, entry.header.mode & 07777
            raise Error, 'Duplicate non-directory archive member: ' + relative if inventory.key?(relative) && kind != '5'
            case kind
            when '5'
              FileUtils.mkdir_p(path)
              File.chmod(mode, path)
              inventory[relative] = {'type' => 'directory', 'mode' => mode}
            when '0', "\0", ''
              raise Error, 'Archive member exceeds 1 GiB' if entry.size > 1024**3
              FileUtils.mkdir_p(File.dirname(path))
              hash = Digest::SHA256.new
              File.open(path, 'wx', mode) do |file|
                until entry.eof?
                  chunk = entry.read(1024 * 1024)
                  raise Error, 'Truncated archive member' unless chunk
                  hash.update(chunk)
                  file.write(chunk)
                end
              end
              File.chmod(mode, path)
              inventory[relative] = {'type' => 'file', 'mode' => mode, 'sha256' => hash.hexdigest}
            when '1', '2'
              target = if kind == '1'
                member_path.call(entry.header.linkname)
              elsif entry.header.linkname.start_with?('/')
                File.expand_path(root + entry.header.linkname)
              else
                File.expand_path(entry.header.linkname, File.dirname(path))
              end
              raise Error, 'Archive link escapes sysroot' unless inside.call(target) || target == root
              links[path] = [kind, target, entry.header.linkname]
              inventory[relative] = {'type' => kind == '1' ? 'hardlink' : 'symlink', 'mode' => mode, 'archive_link' => entry.header.linkname}
            else
              raise Error, 'Unsupported archive entry: ' + relative
            end
          end
        end
        padding_bytes = 0
        until output.eof?
          padding = output.read(65536)
          padding_bytes += padding.bytesize
          raise Error, 'Excessive trailing tar padding' if padding_bytes > 1024 * 1024
          raise Error, 'Nonzero data after tar end marker' unless padding.bytes.all?(&:zero?)
        end
        raise Error, 'xz failed: ' + error.read unless thread.value.success?
      end
    end
    # No symlink exists while regular data are written. Forward hardlinks are
    # resolved only to this snapshot's files; host absolute links are never used.
    hardlinks = links.select { |_, values| values[0] == '1' }
    until hardlinks.empty?
      completed = []
      hardlinks.each do |path, (_, target, _)|
        next unless File.file?(target) && !File.symlink?(target)
        FileUtils.mkdir_p(File.dirname(path))
        File.link(target, path)
        completed << path
      end
      raise Error, 'Unresolved or cyclic archive hardlinks' if completed.empty?
      completed.each { |path| hardlinks.delete(path) }
    end
    links.each do |path, (kind, target, _)|
      next unless kind == '2'
      parent = File.dirname(path)
      until parent == root
        raise Error, 'Archive link has a symlink parent' if File.symlink?(parent)
        parent = File.dirname(parent)
      end
      FileUtils.mkdir_p(File.dirname(path))
      normalized = Pathname.new(target).relative_path_from(Pathname.new(File.dirname(path))).to_s
      File.symlink(normalized, path)
      inventory.fetch(path.delete_prefix(root + '/'))['link'] = normalized
    end
    inventory
  end
end
