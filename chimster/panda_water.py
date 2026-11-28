"""Panda water preview with analytic sky reflection, not scene reflection."""
VERTEX="""#version 130
uniform mat4 p3d_ModelViewProjectionMatrix;
uniform mat4 p3d_ModelMatrix;
in vec4 p3d_Vertex;
out vec3 world;
void main(){
 world=(p3d_ModelMatrix*p3d_Vertex).xyz;
 gl_Position=p3d_ModelViewProjectionMatrix*p3d_Vertex;
}"""
FRAGMENT="""#version 130
in vec3 world;
uniform vec3 eye;
uniform vec3 water_color;
uniform vec3 sky_color;
uniform vec3 sun;
uniform float time;
uniform float fog_density;
out vec4 fragColor;
void main(){
 vec2 p=world.xy;
 float a=sin(p.x*.83+p.y*.51+time*1.5);
 float b=cos(p.x*.36-p.y*1.12-time*.94);
 vec3 n=normalize(vec3(.12*a,.13*b,1.0));
 vec3 v=normalize(eye-world);
 if(v.z<0.0)n=-n;
 vec3 r=reflect(-v,n);
 float fresnel=.02+.98*pow(1.0-max(dot(n,v),0.0),5.0);
 vec3 sky=mix(sky_color,vec3(.65,.78,.91),clamp(r.z,0.0,1.0));
 float sparkle=pow(max(dot(r,normalize(sun)),0.0),96.0);
 vec3 rgb=mix(water_color,sky,fresnel)+vec3(sparkle*.65);
 float fog=1.0-exp(-fog_density*length(eye-world));
 fragColor=vec4(mix(rgb,sky_color,fog),.82);
}"""

def create_water(root,effects):
    from panda3d.core import CardMaker,Shader,TransparencyAttrib
    e=effects.water_extent
    card=CardMaker("preview-water")
    card.set_frame(-e,e,-e,e)
    node=root.attach_new_node(card.generate())
    node.set_p(-90)
    node.set_z(effects.water_level)
    node.set_two_sided(True)
    node.set_transparency(TransparencyAttrib.M_alpha)
    node.set_depth_write(False)
    node.set_bin("transparent",0)
    node.set_shader(Shader.make(Shader.SL_GLSL,VERTEX,FRAGMENT))
    node.set_shader_input("water_color",effects.water_color)
    node.set_shader_input("sky_color",effects.fog_color)
    node.set_shader_input("fog_density",effects.fog_density)
    return node
