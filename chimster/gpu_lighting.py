"""Shared GLSL direct-light uniforms and bounded local light evaluation."""
from math import cos,radians
from .shadow_math import unit

GLSL="""
uniform float ambient_level,sun_intensity;
uniform vec3 sun_color;
uniform int light_count;
uniform vec4 light_position[4],light_color[4],light_cone[4];
vec3 local_light(int i,vec3 p,out vec3 l){
 vec3 delta=light_position[i].xyz-p;
 float distance=length(delta);
 l=delta/max(distance,1e-5);
 float radius=light_position[i].w;
 float atten=pow(max(0.0,1.0-distance/radius),2.0);
 float cone=light_cone[i].w;
 if(cone>-1.0)atten*=smoothstep(cone,min(1.0,cone+.12),dot(-l,light_cone[i].xyz));
 return light_color[i].rgb*light_color[i].a*atten;
}
"""
def bind(program,effects):
    from array import array
    for key,value in (("ambient_level",effects.ambient),("sun_intensity",effects.sun_intensity),("sun_color",effects.sun_color),("light_count",len(effects.lights))):
        if key in program:program[key].value=value
    pos=[];color=[];cone=[]
    for light in effects.lights:
        pos.extend((*light.position,light.radius))
        color.extend((*light.color,light.intensity))
        cone.extend((*unit(light.direction),cos(radians(light.cone/2))) if light.direction is not None else (0,0,1,-1))
    for key,data in (("light_position",pos),("light_color",color),("light_cone",cone)):
        if key in program:
            data.extend([0.]*(16-len(data)))
            program[key].write(array("f",data).tobytes())
