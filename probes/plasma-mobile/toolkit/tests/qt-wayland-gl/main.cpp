// SPDX-License-Identifier: BSD-2-Clause
// Origin: EmberBSD (AI-assisted). Installed Qt Wayland/EGL GPU consumer.
#include <QDebug>
#include <QGuiApplication>
#include <QOpenGLContext>
#include <QOpenGLFunctions>
#include <QOpenGLShaderProgram>
#include <QOpenGLWindow>
#include <QSurfaceFormat>
#include <QTimer>
#include <QVector4D>
#include <array>
#include <cstdio>
#include <cstring>
#include <memory>
#include <link_elf.h>

static int loadedLibrary(dl_phdr_info *info, size_t, void *)
{
    if (info->dlpi_name && *info->dlpi_name)
        std::printf("loaded=%s\n", info->dlpi_name);
    return 0;
}

class Window final : public QOpenGLWindow
{
public:
    explicit Window(bool wrongPixel) : m_wrongPixel(wrongPixel)
    {
        resize(640, 400);
        setTitle(QStringLiteral("EmberBSD Qt Wayland V3D check"));
        connect(this, &QOpenGLWindow::frameSwapped, this, [this] {
            if (!m_pending || m_failed)
                return;
            m_pending = false;
            std::printf("frame=%u shader-pixels=1024 swap=Qt\n", ++m_frame);
            if (m_frame == 16) {
                dl_iterate_phdr(loadedLibrary, nullptr);
                QCoreApplication::exit(0);
            } else {
                QTimer::singleShot(100, this, [this] { update(); });
            }
        });
    }

    ~Window() override
    {
        if (context() && context()->isValid()) {
            makeCurrent();
            if (m_vertices)
                m_gl->glDeleteBuffers(1, &m_vertices);
            m_program.reset();
            doneCurrent();
        }
    }

    bool complete() const { return !m_failed && m_frame == 16; }

protected:
    void initializeGL() override
    {
        m_gl = context()->functions();
        m_gl->initializeOpenGLFunctions();
        const auto *renderer = reinterpret_cast<const char *>(m_gl->glGetString(GL_RENDERER));
        const auto *version = reinterpret_cast<const char *>(m_gl->glGetString(GL_VERSION));
        auto *egl = context()->nativeInterface<QNativeInterface::QEGLContext>();
        if (!context()->isOpenGLES() || !egl || !egl->display() || !egl->nativeContext()
            || !renderer || std::strncmp(renderer, "V3D ", 4) != 0) {
            fail("Expected actual Wayland EGL/OpenGLES V3D context");
            return;
        }
        std::printf("renderer=%s\nversion=%s\nQt=%s\n", renderer, version ? version : "", qVersion());
        QOpenGLShaderProgram invalid;
        if (invalid.addShaderFromSourceCode(QOpenGLShader::Fragment, "invalid GLSL input")) {
            fail("Invalid shader unexpectedly compiled");
            return;
        }
        std::puts("rejected=invalid-shader");
        m_program = std::make_unique<QOpenGLShaderProgram>();
        if (!m_program->addShaderFromSourceCode(QOpenGLShader::Vertex,
                "attribute vec2 position; void main() { gl_Position = vec4(position, 0.0, 1.0); }")
            || !m_program->addShaderFromSourceCode(QOpenGLShader::Fragment,
                "precision mediump float; uniform vec4 color; void main() { gl_FragColor = color; }")) {
            fail("Valid shader compile failed");
            return;
        }
        m_program->bindAttributeLocation("position", 0);
        if (!m_program->link()) {
            fail("Shader link failed");
            return;
        }
        const GLfloat triangle[] = {-1, -1, 3, -1, -1, 3};
        m_gl->glGenBuffers(1, &m_vertices);
        m_gl->glBindBuffer(GL_ARRAY_BUFFER, m_vertices);
        m_gl->glBufferData(GL_ARRAY_BUFFER, sizeof(triangle), triangle, GL_STATIC_DRAW);
        if (!m_vertices || m_gl->glGetError() != GL_NO_ERROR)
            fail("Vertex buffer allocation failed");
    }

    void paintGL() override
    {
        if (m_failed || m_frame >= 16)
            return;
        const std::array<std::array<GLubyte, 4>, 4> colors{{
            {{255, 0, 0, 255}}, {{0, 255, 0, 255}},
            {{0, 0, 255, 255}}, {{255, 0, 255, 255}}
        }};
        const auto &color = colors[m_frame % colors.size()];
        const int w = qRound(width() * devicePixelRatio());
        const int h = qRound(height() * devicePixelRatio());
        if (w < 32 || h < 32 || !m_program->bind()) {
            fail("Invalid surface or shader binding");
            return;
        }
        m_gl->glViewport(0, 0, w, h);
        m_gl->glDisable(GL_DITHER);
        m_gl->glBindBuffer(GL_ARRAY_BUFFER, m_vertices);
        m_program->enableAttributeArray(0);
        m_program->setAttributeBuffer(0, GL_FLOAT, 0, 2);
        m_program->setUniformValue("color", QVector4D(color[0] / 255.0f,
            color[1] / 255.0f, color[2] / 255.0f, 1.0f));
        m_gl->glDrawArrays(GL_TRIANGLES, 0, 3);
        std::array<GLubyte, 32 * 32 * 4> pixels{};
        m_gl->glReadPixels(w / 2 - 16, h / 2 - 16, 32, 32,
            GL_RGBA, GL_UNSIGNED_BYTE, pixels.data());
        m_program->disableAttributeArray(0);
        m_program->release();
        if (m_gl->glGetError() != GL_NO_ERROR) {
            fail("GL draw/readback error");
            return;
        }
        for (size_t i = 0; i < pixels.size(); ++i) {
            const auto expected = m_wrongPixel ? GLubyte(17) : color[i % 4];
            if (pixels[i] != expected) {
                fail("Shader pixel mismatch");
                return;
            }
        }
        m_pending = true;
    }

private:
    void fail(const char *message)
    {
        m_failed = true;
        qCritical() << "FAIL:" << message;
        QCoreApplication::exit(3);
    }
    QOpenGLFunctions *m_gl = nullptr;
    std::unique_ptr<QOpenGLShaderProgram> m_program;
    GLuint m_vertices = 0;
    unsigned m_frame = 0;
    bool m_wrongPixel = false, m_pending = false, m_failed = false;
};

int main(int argc, char **argv)
{
    std::setvbuf(stdout, nullptr, _IONBF, 0);
    QSurfaceFormat format;
    format.setRenderableType(QSurfaceFormat::OpenGLES);
    format.setVersion(2, 0);
    format.setSwapInterval(1);
    QSurfaceFormat::setDefaultFormat(format);
    QGuiApplication app(argc, argv);
    if (QGuiApplication::platformName() != QStringLiteral("wayland")) {
        qCritical() << "FAIL: actual Wayland QPA required";
        return 2;
    }
    int status;
    bool complete;
    {
        Window window(app.arguments().contains(QStringLiteral("--wrong-pixel")));
        QTimer deadline;
        deadline.setSingleShot(true);
        QObject::connect(&deadline, &QTimer::timeout, &app, [] {
            qCritical() << "FAIL: Wayland GPU frame deadline";
            QCoreApplication::exit(4);
        });
        deadline.start(20000);
        window.show();
        status = app.exec();
        complete = window.complete();
    }
    if (status == 0 && complete)
        std::puts("PASS: Qt Wayland V3D shader pixels, sixteen swaps and resource destruction");
    else if (status == 0)
        status = 5;
    return status;
}
