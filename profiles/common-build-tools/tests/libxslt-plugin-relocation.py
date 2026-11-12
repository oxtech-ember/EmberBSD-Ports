#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Exercise real libxslt plugin lookup in an isolated, relocated Darwin prefix.

The prefix must be a disposable installed SDK, never the live build prefix.
Only a uniquely named test module is created there; it is removed on exit.
"""
import argparse
import os
from pathlib import Path
import subprocess
import tempfile
import uuid

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--prefix', type=Path, required=True)
p.add_argument('--cc', type=Path, required=True)
p.add_argument('--work', type=Path, required=True)
a = p.parse_args()
for value in (a.prefix, a.cc, a.work):
    if not value.is_absolute():
        p.error('paths must be absolute')
if os.uname().sysname != 'Darwin':
    p.error('this runtime check requires Darwin')
a.work.mkdir(parents=True, exist_ok=True)
env = dict(os.environ)
for name in list(env):
    if name.startswith('DYLD_') or name == 'LIBXSLT_PLUGINS_PATH':
        del env[name]
name = 'ember_relocation_' + uuid.uuid4().hex
uri = 'https://' + name
directory = a.prefix / 'lib/libxslt-plugins'
created_directory = not directory.exists()
directory.mkdir(exist_ok=True)
module = directory / (name + '.so')

with tempfile.TemporaryDirectory(prefix='libxslt-plugin-', dir=a.work) as temp:
    work = Path(temp)
    source = work / 'plugin.c'
    source.write_text('''#include <libxml/xpathInternals.h>
#include <libxslt/extensions.h>
static void value(xmlXPathParserContextPtr ctxt, int nargs)
{
    if (nargs != 0) {
        xmlXPathSetArityError(ctxt);
        return;
    }
    xmlXPathReturnString(ctxt, xmlStrdup(BAD_CAST "moved-ok"));
}
void ''' + name + '''_init(void)
{
    xsltRegisterExtModuleFunction(BAD_CAST "value", BAD_CAST "''' + uri + '''", value);
}
''')
    style = work / 'style.xsl'
    style.write_text('''<xsl:stylesheet version="1.0"
 xmlns:xsl="http://www.w3.org/1999/XSL/Transform" xmlns:t="''' + uri + '''">
<xsl:output method="text"/>
<xsl:template match="/"><xsl:value-of select="t:value()"/></xsl:template>
</xsl:stylesheet>''')
    data = work / 'input.xml'
    data.write_text('<root/>')
    command = [str(a.prefix / 'bin/xsltproc'), str(style), str(data)]
    try:
        subprocess.run([str(a.cc), '-dynamiclib', '-Wall', '-Wextra', '-Werror',
                        '-I' + str(a.prefix / 'include'),
                        '-I' + str(a.prefix / 'include/libxml2'), str(source),
                        '-L' + str(a.prefix / 'lib'), '-lxslt', '-lxml2',
                        '-Wl,-rpath,@loader_path/..', '-o', str(module)],
                       check=True, env=env)
        result = subprocess.run(command, env=env, capture_output=True, text=True)
        assert result.returncode == 0 and result.stdout == 'moved-ok', result
        # A missing module must remain an error, not a stale loaded module or
        # a fallback to the producer's SDK. Each invocation is a new process.
        removed = work / module.name
        module.rename(removed)
        result = subprocess.run(command, env=env, capture_output=True, text=True)
        assert result.returncode != 0 and 'moved-ok' not in result.stdout, result
        # Preserve the public, explicit plugin-directory override.
        result = subprocess.run(command, env=dict(env, LIBXSLT_PLUGINS_PATH=str(work)),
                                capture_output=True, text=True)
        assert result.returncode == 0 and result.stdout == 'moved-ok', result
        print('PASS moved-prefix plugin lookup, missing plugin, explicit override')
    finally:
        module.unlink(missing_ok=True)
        if created_directory:
            directory.rmdir()
