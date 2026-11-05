#include <QGuiApplication>
#include <QFile>
#include <QResource>
#include <latex.h>

int main(int argc, char **argv)
{
    QGuiApplication app(argc, argv);
    Q_INIT_RESOURCE(bundled);
    if (!QFile::exists(":/res/fonts/base/cmex10.ttf"))
        return 1;
    tex::LaTeX::initBundled();
    tex::LaTeX::release();
    return 0;
}
