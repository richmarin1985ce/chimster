"""Shared bounded volumetric integration in world space."""
from array import array
GLSL="""
uniform vec3 camera_eye,camera_right,camera_up,camera_forward;
uniform int volume_steps,volume_count;
uniform float volume_distance,fog_height,fog_falloff;
uniform vec4 volume_sphere[4];
uniform float volume_density[4];
uniform vec3 world_sun;
float density_at(vec3 origin,vec3 ray,float start,float end){
 float ds=max(end-start,1e-6);
 vec3 p=origin+ray*((start+end)*.5);
 float d=fog_density*exp(-fog_falloff*max(0.0,p.z-fog_height));
 for(int i=0;i<volume_count;i++){
   vec4 sphere=volume_sphere[i];
   vec3 offset=origin-sphere.xyz;
   float b=dot(offset,ray);
   float disc=b*b-dot(offset,offset)+sphere.w*sphere.w;
   if(disc<=0.0)continue;
   float root=sqrt(disc);
   float a=max(start,-b-root),z=min(end,-b+root);
   if(z<=a)continue;
   float r=length(origin+ray*((a+z)*.5)-sphere.xyz)/sphere.w;
   d+=volume_density[i]*(1.0-smoothstep(.65,1.0,r))*(z-a)/ds;
 }
 return d;
}
float phase_hg(float mu){
 float gg=anisotropy*anisotropy;
 return (1.0-gg)/pow(max(.01,1.0+gg-2.0*anisotropy*mu),1.5);
}
vec3 integrate_fog(vec3 src,vec3 view_pos){
 vec3 direction=normalize(camera_right*view_pos.x+camera_up*view_pos.y+camera_forward*view_pos.z);
 float distance=min(length(view_pos),volume_distance);
 float ds=distance/float(volume_steps);
 float trans=1.0;
 vec3 accumulated=vec3(0.0);
 float phase=phase_hg(dot(direction,normalize(world_sun)));
 for(int i=0;i<24;i++){
   if(i>=volume_steps||trans<.005)break;
   vec3 p=camera_eye+direction*((float(i)+.5)*ds);
   float density=density_at(camera_eye,direction,float(i)*ds,float(i+1)*ds);
   float a=1.0-exp(-density*ds);
   if(a<1e-6)continue;
   vec3 radiance=fog_color*ambient_level;
   if(scatter_strength>0.0){
     float visible=sun_visibility(p,0.0,false);
     radiance+=fog_color*sun_color*sun_intensity*visible*scatter_strength*phase*.15;
     for(int j=0;j<light_count;j++){
       vec3 toward;vec3 local=local_light(j,p,toward);
       radiance+=local*local_visibility(j,p)*scatter_strength*phase_hg(dot(direction,toward))*.12;
     }
   }
   accumulated+=trans*a*radiance;
   trans*=1.0-a;
 }
 return src*trans+accumulated;
}
"""
def bind(program,effects,view,settings):
    eye,right,up,back,_,_=view
    values=dict(camera_eye=eye,camera_right=right,camera_up=up,camera_forward=tuple(-x for x in back),world_sun=settings.light,volume_steps=effects.volume_steps,volume_count=len(effects.fog_volumes),volume_distance=effects.volume_distance,fog_height=effects.fog_height,fog_falloff=effects.fog_falloff)
    for key,value in values.items():program[key].value=value
    spheres=[];densities=[]
    for volume in effects.fog_volumes:
        spheres.extend((*volume.center,volume.radius));densities.append(volume.density)
    spheres.extend([0.]*(16-len(spheres)));densities.extend([0.]*(4-len(densities)))
    program["volume_sphere"].write(array("f",spheres).tobytes())
    program["volume_density"].write(array("f",densities).tobytes())

def sphere_segment(origin,ray,center,radius,start,end):
    """CPU reference for the bounded ray/sphere overlap (normalized ray)."""
    from math import sqrt
    offset=tuple(a-b for a,b in zip(origin,center))
    b=sum(a*x for a,x in zip(offset,ray))
    discriminant=b*b-sum(a*a for a in offset)+radius*radius
    if discriminant<=0:return None
    root=sqrt(discriminant);a=max(start,-b-root);z=min(end,-b+root)
    return (a,z) if z>a else None
