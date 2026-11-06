# LevelDB source

`source.py` prepares and verifies the common `databases/leveldb` release and
complete Ports patch set using the existing network archive owner. Select the
SDK source, archive, patch tool, and output explicitly; `--help` lists options.

`test-source.py --sdk-source SDK --archive leveldb-1.23.tar.gz --patch PATCH
--git GIT` exercises preparation from the verified upstream archive, the complete
recipe patch inventory, and rejection of altered archive and patch bytes.
