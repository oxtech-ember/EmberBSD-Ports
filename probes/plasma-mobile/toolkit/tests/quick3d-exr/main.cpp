// SPDX-License-Identifier: BSD-2-Clause
#include <QtCore/QBuffer>
#include <QtCore/QFile>
#include <QtCore/QSharedPointer>
#include <QtQuick3DRuntimeRender/private/qssgrenderloadedtexture_p.h>
#include <cmath>
#include <cstdio>

static QSSGLoadedTexture *load(const QByteArray &bytes)
{
    auto buffer = QSharedPointer<QBuffer>::create();
    buffer->setData(bytes);
    if (!buffer->open(QIODevice::ReadOnly))
        return nullptr;
    return QSSGLoadedTexture::loadHdrImage(buffer, QSSGRenderTextureFormat::RGBA32F);
}

int main(int argc, char **argv)
{
    if (argc != 2) return 1;
    QFile file(QString::fromLocal8Bit(argv[1]));
    if (!file.open(QIODevice::ReadOnly)) return 1;
    const QByteArray bytes = file.readAll();
    for (int n = 0; n <= 8; ++n) {
        auto image = load(bytes.left(n));
        if (image) { delete image; return 2; }
    }
    auto image = load(bytes);
    if (!image || image->width != 64 || image->height != 64 || !image->data) return 3;
    const auto *p = static_cast<const float *>(image->data);
    for (int i = 0; i < 64 * 64 * 4; ++i)
        if (std::fabs(p[i] - float(i % 16) / 16.0f) > 0.0001f) return 4;
    delete image;
    std::puts("Qt Quick3D EXR 0..8-byte boundaries and pixels PASS");
    return 0;
}
