// SPDX-License-Identifier: BSD-2-Clause
// Origin: EmberBSD contributors (AI-assisted).
#include <xatlas.h>
#include <cstdio>
int main() {
 const float positions[]={0,0,0, 1,0,0, 0,1,0};
 const unsigned indices[]={0,1,2};
 xatlas::Atlas *atlas=xatlas::Create();
 xatlas::MeshDecl mesh; mesh.vertexCount=3; mesh.vertexPositionData=positions; mesh.vertexPositionStride=3*sizeof(float); mesh.indexData=indices; mesh.indexCount=3; mesh.indexFormat=xatlas::IndexFormat::UInt32;
 if (xatlas::AddMesh(atlas,mesh)!=xatlas::AddMeshError::Success) return 2;
 xatlas::Generate(atlas);
 bool ok=atlas->meshCount==1 && atlas->meshes[0].indexCount==3 && atlas->width>0 && atlas->height>0;
 xatlas::Destroy(atlas); if (!ok) return 3;
 std::puts("xatlas triangle PASS"); return 0;
}
