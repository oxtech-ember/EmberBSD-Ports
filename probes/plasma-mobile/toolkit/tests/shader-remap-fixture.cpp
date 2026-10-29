#include "qspirvshaderremap_p.h"
#include <QCoreApplication>
#include <QFile>
int main(int argc,char **argv) {
 QCoreApplication app(argc,argv); QFile file(argv[1]); if (!file.open(QIODevice::ReadOnly)) return 1;
 QByteArray input=file.readAll(); QSpirvShaderRemapper remap;
 for (int i=0;i<2;++i) { auto flags=i ? QSpirvShader::RemapFlags{} : QSpirvShader::RemapFlags{QSpirvShader::RemapFlag::StripOnly}; QByteArray result=remap.remap(input,flags); if(result.isEmpty() || !remap.errorMessage().isEmpty()) return 2; QFile out(QString::fromUtf8(argv[i+2])); if (!out.open(QIODevice::WriteOnly) || out.write(result)!=result.size()) return 3; }
 if (!remap.remap(QByteArray("bad",3),{}).isEmpty() || remap.errorMessage().isEmpty()) return 4;
 if (!remap.remap(QByteArray(8,'x'),{}).isEmpty() || remap.errorMessage().isEmpty()) return 5;
 if (!remap.remap({},{}).isEmpty() || !remap.errorMessage().isEmpty()) return 6;
 return 0;
}
