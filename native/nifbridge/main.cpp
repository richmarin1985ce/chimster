// SPDX-License-Identifier: GPL-3.0-only
// Independently authored helper linked with GPL-3.0 nifly.
#include "NifFile.hpp"
#include <fstream>
#include <sstream>
#include <iomanip>
#include <iostream>
#include <cmath>
#include <map>
#include <stdexcept>
#include <filesystem>
using namespace nifly;
struct Expected { size_t vertices, triangles; std::string diffuse,normal; bool cutout; };
static void require(bool ok,const char* message){if(!ok)throw std::runtime_error(message);}
int main(int argc,char** argv){
 try {
    require(argc==4,"usage: chimster-nifbridge GAME INPUT.cmesh OUTPUT.nif");
    std::string game=argv[1]; unsigned user=12,stream=0;
    if(game=="newvegas"||game=="fallout3"){user=11;stream=34;}
    else if(game=="skyrim")stream=83;
    else if(game=="skyrimse"||game=="skyrimvr")stream=100;
    else if(game=="fallout4"||game=="fallout4vr")stream=130;
    else throw std::runtime_error("unsupported game");
    require(!std::filesystem::exists(argv[3]),"output already exists");
    std::ifstream in(argv[2]);require(bool(in),"cannot open mesh");
    std::string magic;unsigned n;in>>magic>>n;require(bool(in)&&magic=="CHIMSTER_MESH_1"&&n>0&&n<=256,"invalid mesh header");
    NifFile nif;nif.Create(NiVersion(NiFileVersion::V20_2_0_7,user,stream));
    std::map<std::string,Expected> expected;
    for(unsigned s=0;s<n;s++){
      std::string name,diffuse,normal; unsigned nv,nt,cut;
      in>>std::quoted(name)>>std::quoted(diffuse)>>std::quoted(normal)>>cut>>nv>>nt;
      require(bool(in)&&!name.empty()&&name.size()<=100&&nv>0&&nv<=65535&&nt>0&&nt<=65535&&cut<=1,"invalid shape header");
      require(!expected.count(name),"duplicate shape");
      std::vector<Vector3> verts,normals;std::vector<Vector2> uv;std::vector<Triangle> tris;
      verts.reserve(nv);normals.reserve(nv);uv.reserve(nv);tris.reserve(nt);
      for(unsigned i=0;i<nv;i++){
        float x,y,z,u,v,nx,ny,nz;in>>x>>y>>z>>u>>v>>nx>>ny>>nz;
        require(bool(in)&&std::isfinite(x)&&std::isfinite(y)&&std::isfinite(z)&&std::isfinite(u)&&std::isfinite(v)&&std::isfinite(nx)&&std::isfinite(ny)&&std::isfinite(nz),"invalid vertex");
        verts.emplace_back(x,y,z);uv.emplace_back(u,v);normals.emplace_back(nx,ny,nz);
      }
      for(unsigned i=0;i<nt;i++){
        unsigned a,b,c;in>>a>>b>>c;require(bool(in)&&a<nv&&b<nv&&c<nv&&a!=b&&b!=c&&a!=c,"invalid triangle");
        tris.emplace_back(static_cast<uint16_t>(a),static_cast<uint16_t>(b),static_cast<uint16_t>(c));
      }
      auto shape=nif.CreateShapeFromData(name,&verts,&tris,&uv,&normals);
      require(shape!=nullptr&&nif.GetShader(shape)!=nullptr,"shape creation failed");
      if(!diffuse.empty())nif.SetTextureSlot(shape,diffuse,0);
      if(!normal.empty())nif.SetTextureSlot(shape,normal,1);
      nif.CalcTangentsForShape(shape);
      if(cut){
        auto alpha=std::make_unique<NiAlphaProperty>();
        alpha->flags=0x1200;alpha->threshold=128;
        nif.AssignAlphaProperty(shape,std::move(alpha));
      }
      expected.emplace(name,Expected{nv,nt,diffuse,normal,cut!=0});
    }
    std::string extra;require(!(in>>extra),"trailing input");
    // Serialize into memory first so a rejected output is not published.
    std::ostringstream out(std::ios::binary|std::ios::out);
    require(nif.Save(out)==0,"NIF save failed");
    std::string bytes=out.str();std::istringstream input(bytes,std::ios::binary|std::ios::in);
    NifFile check;require(check.Load(input)==0&&check.IsValid()&&!check.HasUnknown(),"NIF reopen failed");
    const auto& ver=check.GetHeader().GetVersion();
    require(ver.File()==NiFileVersion::V20_2_0_7&&ver.User()==user&&ver.Stream()==stream,"version mismatch");
    auto shapes=check.GetShapes();require(shapes.size()==expected.size(),"shape count mismatch");
    size_t count=0;
    for(auto shape:shapes){
      auto e=expected.at(shape->name.get());std::vector<Vector3> v;std::vector<Triangle> t;
      require(check.GetVertsForShape(shape,v)&&shape->GetTriangles(t)&&v.size()==e.vertices&&t.size()==e.triangles,"geometry count mismatch");
      std::string tex;
      if(!e.diffuse.empty()){check.GetTextureSlot(shape,tex,0);require(tex==e.diffuse,"diffuse mismatch");}
      if(!e.normal.empty()){check.GetTextureSlot(shape,tex,1);require(tex==e.normal,"normal mismatch");}
      require(!e.cutout||check.GetAlphaProperty(shape)!=nullptr,"missing alpha property");count+=t.size();
    }
    std::ofstream result(argv[3],std::ios::binary);require(bool(result),"cannot create output");result.write(bytes.data(),bytes.size());require(bool(result),"write failed");
    std::cout<<"{\"shapes\":"<<shapes.size()<<",\"triangles\":"<<count<<",\"user_version\":"<<user<<",\"stream_version\":"<<stream<<"}\n";
    return 0;
 }catch(const std::exception& e){std::cerr<<e.what()<<"\n";return 1;}
}
