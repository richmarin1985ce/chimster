// SPDX-License-Identifier: GPL-3.0-only
// Independently authored helper linked with GPL-3.0 nifly.
#include "NifFile.hpp"
#include "bhk.hpp"
#include "ExtraData.hpp"
#include <limits>
#include <algorithm>
#include <fstream>
#include <sstream>
#include <iomanip>
#include <iostream>
#include <cmath>
#include <map>
#include <stdexcept>
#include <filesystem>
#include <functional>
#include <set>
#include <array>
using namespace nifly;
struct CollisionBox { float lo[3],hi[3]; unsigned material; };
struct Expected { size_t vertices, triangles; std::string diffuse,normal; bool cutout; };
static void require(bool ok,const char* message){if(!ok)throw std::runtime_error(message);}
// Read native static root collision only. Fail closed on unsupported shapes.
static int extractCollision(const char* filename,const char* scaleArg){
    float scale=std::stof(scaleArg);require(std::isfinite(scale)&&scale>0&&scale<=100000,"explicit Havok unit scale required");
    require(std::filesystem::file_size(filename)<=128*1024*1024,"NIF input limit");
    std::ifstream input(filename,std::ios::binary);NifFile nif;
    require(bool(input)&&nif.Load(input)==0&&nif.IsValid()&&!nif.HasUnknown(),"invalid or unknown NIF");
    auto& h=nif.GetHeader();const auto& ver=h.GetVersion();
    const bool legacy=ver.User()==11&&ver.Stream()==34;
    const bool skyrim=ver.User()==12&&(ver.Stream()==83||ver.Stream()==100);
    require(ver.File()==NiFileVersion::V20_2_0_7&&(legacy||skyrim),"unsupported collision format");
    auto root=nif.GetRootNode();require(root,"missing root");
    auto m=root->GetTransformToParent().ToMatrix();
    for(int i=0;i<16;i++)require(std::abs(m[i]-(i%5==0?1.f:0.f))<1e-5f,"nonidentity root transform unsupported");
    auto coll=dynamic_cast<bhkCollisionObject*>(h.GetBlock(root->collisionRef));
    require(coll&&coll->targetRef.index==nif.GetBlockID(root),"expected root collision");
    unsigned collisionCount=0;
    for(unsigned i=0;i<h.GetNumBlocks();i++)if(h.GetBlock<NiCollisionObject>(i))++collisionCount;
    require(collisionCount==1,"multiple or nested collision objects unsupported");
    auto body=dynamic_cast<bhkRigidBody*>(h.GetBlock(coll->bodyRef));
    require(body&&body->motionSystem==7&&body->mass==0&&body->collisionFilter.layer==1,"expected fixed static collision body");
    // Havok rigid-body transforms are applied in Havok units, before
    // converting to game coordinates. Preserve the documented XYZW order.
    using Transform=std::function<Vector3(Vector3)>;
    auto rigid=[](QuaternionXYZW q,Vector3 tr)->Transform {
        float length=std::sqrt(q.x*q.x+q.y*q.y+q.z*q.z+q.w*q.w);
        require(std::isfinite(length)&&std::abs(length-1.f)<1e-3f,"invalid rigid body quaternion");
        Vector3 u(q.x/length,q.y/length,q.z/length);
        float w=q.w/length;
        return [u,w,tr](Vector3 p){
            Vector3 v=u.cross(p)*2.f;
            return p+v*w+u.cross(v)+tr;
        };
    };
    Transform bodyTransform=[](Vector3 p){return p;};
    if(dynamic_cast<bhkRigidBodyT*>(body))bodyTransform=rigid(body->rotation,Vector3(body->translation.x,body->translation.y,body->translation.z));
    std::vector<Vector3> verts;std::vector<std::array<unsigned,3>> tris;
    std::vector<std::vector<Vector3>> hulls;size_t hullPoints=0;
    std::vector<std::array<float,6>> solids;
    auto scaled=[&](Vector3 p){
        p.x*=scale;p.y*=scale;p.z*=scale;
        require(std::isfinite(p.x)&&std::isfinite(p.y)&&std::isfinite(p.z)&&std::abs(p.x)<=1e7&&std::abs(p.y)<=1e7&&std::abs(p.z)<=1e7,"invalid collision vertex");
        return p;
    };
    auto push=[&](Vector3 p){require(verts.size()<500000,"collision vertex limit");verts.push_back(scaled(p));};
    // Curved primitives are obstruction-only conservative world AABBs.
    // They must not be promoted to walkable triangle surfaces.
    auto solid=[&](Vector3 a,Vector3 b,float r,Transform apply){
        require(std::isfinite(r)&&r>0&&solids.size()<4096,"invalid primitive radius or count");
        a=scaled(apply(a));b=scaled(apply(b));r*=scale;
        std::array<float,6> box={std::min(a.x,b.x)-r,std::min(a.y,b.y)-r,std::min(a.z,b.z)-r,
                                  std::max(a.x,b.x)+r,std::max(a.y,b.y)+r,std::max(a.z,b.z)+r};
        for(float v:box)require(std::isfinite(v)&&std::abs(v)<=1e7,"invalid primitive bounds");
        solids.push_back(box);
    };
    std::set<const bhkShape*> stack;
    std::function<void(bhkShape*,Transform,unsigned)> walk;
    walk=[&](bhkShape* shape,Transform apply,unsigned depth){
        require(shape&&depth<32&&stack.insert(shape).second,"invalid collision shape graph");
        if(auto b=dynamic_cast<bhkBoxShape*>(shape)){
            auto d=b->dimensions;require(d.x>0&&d.y>0&&d.z>0,"invalid box dimensions");
            unsigned base=verts.size();
            for(int z:{-1,1})for(int y:{-1,1})for(int x:{-1,1})push(apply(Vector3(x*d.x,y*d.y,z*d.z)));
            const unsigned faces[12][3]={{0,2,1},{1,2,3},{4,5,6},{5,7,6},{0,1,4},{1,5,4},{2,6,3},{3,6,7},{0,4,2},{2,4,6},{1,3,5},{3,7,5}};
            for(auto& t:faces)tris.push_back({base+t[0],base+t[1],base+t[2]});
        }else if(auto sphere=dynamic_cast<bhkSphereShape*>(shape)){
            solid(Vector3(0,0,0),Vector3(0,0,0),sphere->radius,apply);
        }else if(auto capsule=dynamic_cast<bhkCapsuleShape*>(shape)){
            require(std::isfinite(capsule->radius1)&&std::isfinite(capsule->radius2)&&capsule->radius1>=0&&capsule->radius2>=0&&
                    std::isfinite(capsule->radius)&&capsule->radius>=0,"invalid capsule radii");
            solid(capsule->point1,capsule->point2,std::max({capsule->radius,capsule->radius1,capsule->radius2}),apply);
        }else if(auto cylinder=dynamic_cast<bhkCylinderShape*>(shape)){
            require(std::isfinite(cylinder->cylinderRadius)&&cylinder->cylinderRadius>0&&std::isfinite(cylinder->radius)&&cylinder->radius>=0,"invalid cylinder radius");
            solid(Vector3(cylinder->vertexA.x,cylinder->vertexA.y,cylinder->vertexA.z),
                  Vector3(cylinder->vertexB.x,cylinder->vertexB.y,cylinder->vertexB.z),cylinder->cylinderRadius+cylinder->radius,apply);
        }else if(auto multi=dynamic_cast<bhkMultiSphereShape*>(shape)){
            require(!multi->spheres.empty()&&multi->spheres.size()<=4096,"invalid multisphere count");
            for(const auto& sphere:multi->spheres)solid(sphere.center,sphere.center,sphere.radius,apply);
        }else if(auto convex=dynamic_cast<bhkConvexVerticesShape*>(shape)){
            require(convex->verts.size()>=4&&convex->verts.size()<=64,"convex core point limit");
            require(hulls.size()<128&&hullPoints+convex->verts.size()<=4096,"convex core work limit");
            std::vector<Vector3> points;
            for(const auto& p:convex->verts)points.push_back(scaled(apply(Vector3(p.x,p.y,p.z))));
            hullPoints+=points.size();hulls.push_back(std::move(points));
        }else if(auto list=dynamic_cast<bhkConvexListShape*>(shape)){
            require(list->shapeRefs.GetSize()<=4096,"convex list limit");
            for(unsigned i=0;i<list->shapeRefs.GetSize();i++)walk(h.GetBlock<bhkShape>(list->shapeRefs.GetBlockRef(i)),apply,depth+1);
        }else if(auto tf=dynamic_cast<bhkTransformShape*>(shape)){
            auto m=tf->xform;
            for(int i=0;i<16;i++)require(std::isfinite(m[i]),"nonfinite collision transform");
            require(std::abs(m[3])+std::abs(m[7])+std::abs(m[11])<1e-5f&&std::abs(m[15]-1)<1e-5f,"nonaffine child transform");
            Vector3 a(m[0],m[1],m[2]),b(m[4],m[5],m[6]),c(m[8],m[9],m[10]);
            auto dot=[](Vector3 p,Vector3 q){return p.x*q.x+p.y*q.y+p.z*q.z;};
            require(std::abs(dot(a,a)-1)<1e-4f&&std::abs(dot(b,b)-1)<1e-4f&&std::abs(dot(c,c)-1)<1e-4f&&
                    std::abs(dot(a,b))+std::abs(dot(a,c))+std::abs(dot(b,c))<1e-4f&&dot(a.cross(b),c)>.999f,
                    "child transform must be proper rigid rotation");
            // Same column-major Havok convention as compound exporter.
            Transform child=[m,apply](Vector3 p){return apply(Vector3(m[0]*p.x+m[4]*p.y+m[8]*p.z+m[12],
                m[1]*p.x+m[5]*p.y+m[9]*p.z+m[13],m[2]*p.x+m[6]*p.y+m[10]*p.z+m[14]));};
            walk(h.GetBlock(tf->shapeRef),child,depth+1);
        }else if(auto list=dynamic_cast<bhkListShape*>(shape)){
            require(list->subShapeRefs.GetSize()<=4096,"collision list limit");
            for(unsigned i=0;i<list->subShapeRefs.GetSize();i++)walk(h.GetBlock<bhkShape>(list->subShapeRefs.GetBlockRef(i)),apply,depth+1);
        }else if(auto mopp=dynamic_cast<bhkMoppBvTreeShape*>(shape)){
            walk(h.GetBlock(mopp->shapeRef),apply,depth+1);
        }else if(auto compressed=dynamic_cast<bhkCompressedMeshShape*>(shape)){
            require(skyrim,"compressed collision extraction requires Skyrim format");
            auto data=h.GetBlock(compressed->dataRef);
            require(data&&data->numConvexPieceA==0&&data->chunks.size()<=4096,"unsupported compressed collision data");
            auto unit=[](const Vector4& v){return std::abs(v.x-1)<1e-5f&&std::abs(v.y-1)<1e-5f&&std::abs(v.z-1)<1e-5f;};
            require(unit(compressed->scaling)&&unit(compressed->scaling2),"compressed collision scale unsupported");
            auto append=[&](unsigned base,unsigned count,unsigned a,unsigned b,unsigned c){
                require(a<count&&b<count&&c<count,"compressed triangle index out of range");
                if(a!=b&&b!=c&&a!=c){require(tris.size()<500000,"collision triangle limit");tris.push_back({base+a,base+b,base+c});}
            };
            unsigned base=verts.size();
            require(data->bigVerts.size()<=500000-verts.size(),"big vertex limit");
            for(const auto& p:data->bigVerts)push(apply(Vector3(p.x,p.y,p.z)));
            for(const auto& t:data->bigTris)append(base,data->bigVerts.size(),t.triangle1,t.triangle2,t.triangle3);
            for(const auto& chunk:data->chunks){
                require(chunk.reference==65535,"referenced compressed chunk semantics unverified");
                Transform chunkTransform=[](Vector3 p){return p;};
                if(chunk.transformIndex!=65535){
                    require(chunk.transformIndex<data->transforms.size(),"invalid compressed chunk transform index");
                    const auto& tf=data->transforms[chunk.transformIndex];
                    chunkTransform=rigid(tf.rotation,Vector3(tf.translation.x,tf.translation.y,tf.translation.z));
                }
                require(chunk.verts.size()%3==0&&chunk.verts.size()/3<=500000-verts.size(),"invalid compressed vertex array");
                unsigned count=chunk.verts.size()/3;base=verts.size();
                // Skyrim compressed vertices are quantized at 1/1000 Havok unit.
                for(unsigned j=0;j<chunk.verts.size();j+=3){
                    push(apply(chunkTransform(Vector3(chunk.translation.x+chunk.verts[j]*.001f,
                                       chunk.translation.y+chunk.verts[j+1]*.001f,
                                       chunk.translation.z+chunk.verts[j+2]*.001f))));
                }
                size_t pos=0;
                for(auto length:chunk.strips){
                    require(length>=3&&pos+length<=chunk.indices.size(),"invalid compressed strip length");
                    for(unsigned j=0;j+2<length;j++){
                        auto a=chunk.indices[pos+j],b=chunk.indices[pos+j+1],c=chunk.indices[pos+j+2];
                        if(j%2)std::swap(a,b);
                        append(base,count,a,b,c);
                    }
                    pos+=length;
                }
                require((chunk.indices.size()-pos)%3==0,"invalid compressed triangle list");
                for(;pos<chunk.indices.size();pos+=3)append(base,count,chunk.indices[pos],chunk.indices[pos+1],chunk.indices[pos+2]);
            }
        }else if(auto packed=dynamic_cast<bhkPackedNiTriStripsShape*>(shape)){
            auto data=h.GetBlock(packed->dataRef);
            require(data&&!data->compressed&&data->compressedVertData.size()==data->numVerts,"unsupported packed vertex encoding");
            require(std::abs(packed->scaling.x-1)<1e-5f&&std::abs(packed->scaling.y-1)<1e-5f&&std::abs(packed->scaling.z-1)<1e-5f,"nonunit packed scale unsupported");
            unsigned base=verts.size();
            for(auto p:data->compressedVertData)push(apply(p));
            auto append=[&](const Triangle& t){require(t.p1<data->numVerts&&t.p2<data->numVerts&&t.p3<data->numVerts,"invalid packed triangle");tris.push_back({base+t.p1,base+t.p2,base+t.p3});};
            for(auto& t:data->triData)append(t.tri);
            for(auto& t:data->triNormData)append(t.tri);
        }else throw std::runtime_error("unsupported native collision shape");
        require(tris.size()<=500000,"collision triangle limit");stack.erase(shape);
    };
    walk(h.GetBlock(body->shapeRef),bodyTransform,0);
    require((!verts.empty()&&!tris.empty())||!hulls.empty()||!solids.empty(),"empty collision geometry");
    std::cout<<std::setprecision(9)<<"{\"vertices\":[";
    for(size_t i=0;i<verts.size();i++){if(i)std::cout<<",";auto p=verts[i];std::cout<<"["<<p.x<<","<<p.y<<","<<p.z<<"]";}
    std::cout<<"],\"triangles\":[";
    for(size_t i=0;i<tris.size();i++){if(i)std::cout<<",";auto t=tris[i];std::cout<<"["<<t[0]<<","<<t[1]<<","<<t[2]<<"]";}
    std::cout<<"],\"convex_cores\":[";
    for(size_t i=0;i<hulls.size();i++){if(i)std::cout<<",";std::cout<<"[";for(size_t j=0;j<hulls[i].size();j++){if(j)std::cout<<",";auto p=hulls[i][j];std::cout<<"["<<p.x<<","<<p.y<<","<<p.z<<"]";}std::cout<<"]";}
    std::cout<<"],\"solid_obstacles\":[";
    for(size_t i=0;i<solids.size();i++){if(i)std::cout<<",";auto b=solids[i];std::cout<<"{\"min\":["<<b[0]<<","<<b[1]<<","<<b[2]<<"],\"max\":["<<b[3]<<","<<b[4]<<","<<b[5]<<"]}";}
    std::cout<<"]}\n";return 0;
}
// Static geometry extraction; not a lossless NIF editor.
static int extractMesh(const char* filename){
    require(std::filesystem::file_size(filename)<=128*1024*1024,"NIF input limit");
    std::ifstream input(filename,std::ios::binary);NifFile nif;
    require(bool(input)&&nif.Load(input)==0&&nif.IsValid()&&!nif.HasUnknown(),"invalid or unknown NIF");
    const auto& ver=nif.GetHeader().GetVersion();
    require(ver.File()==NiFileVersion::V20_2_0_7&&
      ((ver.User()==11&&ver.Stream()==34)||(ver.User()==12&&(ver.Stream()==83||ver.Stream()==100||ver.Stream()==130))),"unsupported NIF version");
    auto identity=[](auto* node){
        auto m=node->GetTransformToParent().ToMatrix();
        for(int i=0;i<16;i++)require(std::isfinite(m[i])&&std::abs(m[i]-(i%5==0?1.f:0.f))<1e-5f,"nonidentity transform unsupported");
    };
    auto root=nif.GetRootNode();require(root,"missing root");identity(root);
    auto shapes=nif.GetShapes();require(!shapes.empty()&&shapes.size()<=256,"shape count limit");
    std::ostringstream out;out<<std::setprecision(9)<<"CHIMSTER_IMPORT_1 "<<shapes.size()<<"\n";
    size_t nv=0,nt=0;
    for(size_t i=0;i<shapes.size();i++){
        auto shape=shapes[i];require(nif.GetParentNode(shape)==root&&!shape->IsSkinned()&&!shape->HasSkinInstance(),"only unskinned direct root shapes supported");
        identity(shape);
        std::vector<Vector3> v;std::vector<Vector2> uv;std::vector<Triangle> t;
        require(nif.GetVertsForShape(shape,v)&&nif.GetUvsForShape(shape,uv)&&shape->GetTriangles(t)&&!v.empty()&&!t.empty()&&v.size()==uv.size(),"missing geometry or UVs");
        nv+=v.size();nt+=t.size();require(nv<=300000&&nt<=300000,"geometry limit");
        std::string diffuse,normal;nif.GetTextureSlot(shape,diffuse,0);nif.GetTextureSlot(shape,normal,1);
        auto alpha=nif.GetAlphaProperty(shape);
        require(!alpha||(alpha->flags==0x1200&&alpha->threshold==128),"unsupported alpha property");
        auto safe=[](const std::string& s){return s.size()<=1024&&std::all_of(s.begin(),s.end(),[](unsigned char c){return c>=32&&c<127;});};
        require(safe(diffuse)&&safe(normal),"unsafe texture path");
        out<<"shape_"<<i<<" "<<std::quoted(diffuse)<<" "<<std::quoted(normal)<<" "<<(alpha?1:0)<<" "<<v.size()<<" "<<t.size()<<"\n";
        for(size_t j=0;j<v.size();j++){
            auto p=v[j];auto q=uv[j];
            require(std::isfinite(p.x)&&std::isfinite(p.y)&&std::isfinite(p.z)&&std::isfinite(q.u)&&std::isfinite(q.v),"invalid vertex/UV");
            out<<p.x<<" "<<p.y<<" "<<p.z<<" "<<q.u<<" "<<1-q.v<<"\n";
        }
        for(auto f:t){
            require(f.p1<v.size()&&f.p2<v.size()&&f.p3<v.size()&&f.p1!=f.p2&&f.p2!=f.p3&&f.p1!=f.p3,"invalid triangle");
            out<<f.p1<<" "<<f.p2<<" "<<f.p3<<"\n";
        }
    }
    std::cout<<out.str();return 0;
}
int main(int argc,char** argv){
 try {
    if(argc==3&&std::string(argv[1])=="extract-mesh")return extractMesh(argv[2]);
    if(argc==4&&std::string(argv[1])=="extract-collision")return extractCollision(argv[2],argv[3]);
    require(argc>=4&&argc<=6,"usage: chimster-nifbridge GAME INPUT.cmesh OUTPUT.nif [box|compound FILE]");
    bool box=argc==5&&std::string(argv[4])=="box";
    bool compound=argc==6&&std::string(argv[4])=="compound";
    require(argc==4||box||compound,"invalid collision mode");
    std::string game=argv[1]; unsigned user=12,stream=0;
    if(game=="newvegas"||game=="fallout3"){user=11;stream=34;}
    else if(game=="skyrim")stream=83;
    else if(game=="skyrimse"||game=="skyrimvr")stream=100;
    else if(game=="fallout4"||game=="fallout4vr")stream=130;
    else throw std::runtime_error("unsupported game");
    require(!(box||compound)||stream==34,"experimental box collision is FO3/FNV only");
    require(!std::filesystem::exists(argv[3]),"output already exists");
    std::ifstream in(argv[2]);require(bool(in),"cannot open mesh");
    std::string magic;unsigned n;in>>magic>>n;require(bool(in)&&magic=="CHIMSTER_MESH_1"&&n>0&&n<=256,"invalid mesh header");
    NifFile nif;nif.Create(NiVersion(NiFileVersion::V20_2_0_7,user,stream));
    std::map<std::string,Expected> expected;
    float lo[3]={INFINITY,INFINITY,INFINITY},hi[3]={-INFINITY,-INFINITY,-INFINITY};
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
        float p[3]={x,y,z};for(int k=0;k<3;k++){lo[k]=std::min(lo[k],p[k]);hi[k]=std::max(hi[k],p[k]);}
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
    std::vector<CollisionBox> boxes;
    unsigned listMaterial=0;
    if(compound){
      std::ifstream cin(argv[5]);std::string cmagic;unsigned num;
      cin>>cmagic>>num>>listMaterial;
      require(bool(cin)&&cmagic=="CHIMSTER_COLLISION_1"&&num>0&&num<=256&&listMaterial<=127,"invalid collision recipe");
      for(unsigned i=0;i<num;i++){
        CollisionBox b;
        cin>>b.lo[0]>>b.lo[1]>>b.lo[2]>>b.hi[0]>>b.hi[1]>>b.hi[2]>>b.material;
        require(bool(cin)&&b.material<=127,"invalid material");
        for(int k=0;k<3;k++)require(std::isfinite(b.lo[k])&&std::isfinite(b.hi[k])&&std::abs(b.lo[k])<=1e7&&std::abs(b.hi[k])<=1e7&&b.hi[k]-b.lo[k]>=.001f,"invalid collision box");
        boxes.push_back(b);
      }
      require(!(cin>>extra),"trailing collision input");
    }
    if(box||compound){
      auto& h=nif.GetHeader();auto root=nif.GetRootNode();
      auto makeBox=[&](const CollisionBox& b){
        auto shape=std::make_unique<bhkBoxShape>();
        shape->dimensions=Vector3((b.hi[0]-b.lo[0])/14.f,(b.hi[1]-b.lo[1])/14.f,(b.hi[2]-b.lo[2])/14.f);
        shape->radius=std::min({.05f,shape->dimensions.x*.1f,shape->dimensions.y*.1f,shape->dimensions.z*.1f});
        shape->radius2=shape->radius;shape->SetMaterial(b.material);return shape;
      };
      auto body=std::make_unique<bhkRigidBodyT>();
      if(box){
        CollisionBox b={{lo[0],lo[1],lo[2]},{hi[0],hi[1],hi[2]},0};
        for(int k=0;k<3;k++)require(hi[k]>lo[k],"degenerate collision bounds");
        body->shapeRef.index=h.AddBlock(makeBox(b));
        body->translation=Vector4((hi[0]+lo[0])/14.f,(hi[1]+lo[1])/14.f,(hi[2]+lo[2])/14.f,0);
      }else{
        auto list=std::make_unique<bhkListShape>();list->SetMaterial(listMaterial);
        for(const auto& b:boxes){
          auto child=makeBox(b);
          auto transform=std::make_unique<bhkConvexTransformShape>();
          transform->material=b.material;transform->radius=child->radius;
          transform->shapeRef.index=h.AddBlock(std::move(child));
          // Havok's serialized 4x4 is column-major, translation in final column.
          for(int k=0;k<3;k++)transform->xform[12+k]=(b.hi[k]+b.lo[k])/14.f;
          list->subShapeRefs.AddBlockRef(h.AddBlock(std::move(transform)));
          HavokFilter filter{};list->filters.push_back(filter);
        }
        body->shapeRef.index=h.AddBlock(std::move(list));
        body->translation=Vector4(0,0,0,0);
      }
      body->collisionFilter.layer=1;body->collisionFilterCopy.layer=1;body->motionSystem=7;body->qualityType=1;body->mass=0;body->broadPhaseType=1;
      auto coll=std::make_unique<bhkCollisionObject>();coll->targetRef.index=nif.GetBlockID(root);coll->bodyRef.index=h.AddBlock(std::move(body));
      root->collisionRef.index=h.AddBlock(std::move(coll));
      auto flags=std::make_unique<BSXFlags>();flags->name.get()="BSX";flags->integerData=2;root->extraDataRefs.AddBlockRef(h.AddBlock(std::move(flags)));
    }
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
    if(box||compound){
      auto& h=check.GetHeader();auto root=check.GetRootNode();
      auto coll=dynamic_cast<bhkCollisionObject*>(h.GetBlock(root->collisionRef));require(coll&&coll->targetRef.index==check.GetBlockID(root),"collision object missing");
      auto body=dynamic_cast<bhkRigidBodyT*>(h.GetBlock(coll->bodyRef));require(body&&body->motionSystem==7&&body->collisionFilter.layer==1,"rigid body missing");
      if(box){
        auto shape=dynamic_cast<bhkBoxShape*>(h.GetBlock(body->shapeRef));require(shape&&std::abs(shape->dimensions.x-(hi[0]-lo[0])/14.f)<.0001f,"box missing or incorrect");
      }else{
        auto list=dynamic_cast<bhkListShape*>(h.GetBlock(body->shapeRef));
        require(list&&list->subShapeRefs.GetSize()==boxes.size()&&list->filters.size()==boxes.size()&&list->GetMaterial()==listMaterial,"compound list mismatch");
        for(unsigned k=0;k<boxes.size();k++){
          const auto& b=boxes[k];
          auto tf=h.GetBlock<bhkConvexTransformShape>(list->subShapeRefs.GetBlockRef(k));
          require(tf&&tf->material==b.material,"transform material mismatch");
          auto shape=dynamic_cast<bhkBoxShape*>(h.GetBlock(tf->shapeRef));
          require(shape&&shape->GetMaterial()==b.material,"box material mismatch");
          float expected[3]={(b.hi[0]-b.lo[0])/14.f,(b.hi[1]-b.lo[1])/14.f,(b.hi[2]-b.lo[2])/14.f};
          require(std::abs(shape->dimensions.x-expected[0])<.0001f&&std::abs(shape->dimensions.y-expected[1])<.0001f&&std::abs(shape->dimensions.z-expected[2])<.0001f,"box dimensions mismatch");
          for(int axis=0;axis<3;axis++)require(std::abs(tf->xform[12+axis]-(b.hi[axis]+b.lo[axis])/14.f)<.0001f,"box position mismatch");
        }
      }
    }
    std::ofstream result(argv[3],std::ios::binary);require(bool(result),"cannot create output");result.write(bytes.data(),bytes.size());require(bool(result),"write failed");
    std::cout<<"{\"shapes\":"<<shapes.size()<<",\"triangles\":"<<count<<",\"user_version\":"<<user<<",\"stream_version\":"<<stream<<",\"box_collision\":"<<(box?"true":"false")<<",\"compound_collision\":"<<(compound?"true":"false")<<",\"collision_boxes\":"<<(compound?boxes.size():(box?1:0))<<",\"list_material\":"<<listMaterial<<",\"collision_materials\":[";
    for(unsigned k=0;k<boxes.size();k++){if(k)std::cout<<",";std::cout<<boxes[k].material;}
    std::cout<<"]}\n";
    return 0;
 }catch(const std::exception& e){std::cerr<<e.what()<<"\n";return 1;}
}
