"""Panda water preview with analytic sky and optional planar scene reflection."""
VERTEX="""#version 130
uniform mat4 p3d_ModelViewProjectionMatrix;
uniform mat4 p3d_ModelMatrix;
in vec4 p3d_Vertex;
out vec3 world;
out vec4 screen_pos;
void main(){
 world=(p3d_ModelMatrix*p3d_Vertex).xyz;
 gl_Position=p3d_ModelViewProjectionMatrix*p3d_Vertex;
 screen_pos=gl_Position;
}"""
FRAGMENT="""#version 130
in vec3 world;
in vec4 screen_pos;
uniform sampler2D reflection_tex,refraction_tex,refraction_depth;
uniform float nearp,farp,absorption,foam_strength;
uniform float use_reflection,use_refraction;
uniform vec3 eye;
uniform vec3 water_color;
uniform vec3 sky_color;
uniform vec3 sun;
uniform float time;
uniform float fog_density;
out vec4 fragColor;
float linear_depth(float d){return nearp*farp/(farp-d*(farp-nearp));}
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
 vec2 screen=screen_pos.xy/screen_pos.w*.5+.5;
 vec2 offset=n.xy*.035;
 if(use_reflection>.5)sky=texture(reflection_tex,clamp(vec2(1.0-screen.x,screen.y)+offset,.002,.998)).rgb;
 vec3 body=water_color;
 float foam=0.0;
 if(use_refraction>.5){
   float bottom=texture(refraction_depth,screen).r;
   float thickness=bottom>=.999999?40.0:max(0.0,linear_depth(bottom)-linear_depth(gl_FragCoord.z));
   float optical=thickness/max(.2,abs(dot(v,vec3(0,0,1))));
   vec3 transmitted=texture(refraction_tex,clamp(screen+offset,.002,.998)).rgb;
   body=mix(transmitted,water_color,1.0-exp(-absorption*optical));
   foam=(1.0-smoothstep(.08,.7,thickness))*smoothstep(-.35,.6,a*b)*foam_strength;
 }

 vec3 rgb=mix(body,sky,fresnel)+vec3(sparkle*.65);
 rgb=mix(rgb,vec3(.85,.92,.90),foam);
 float fog=1.0-exp(-fog_density*length(eye-world));
 fragColor=vec4(mix(rgb,sky_color,fog),use_refraction>.5?1.0:.82);
}"""

def create_water(root,effects):
    from panda3d.core import CardMaker,Shader,TransparencyAttrib,Texture
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
    node.set_shader(Shader.make(Shader.SL_GLSL,VERTEX,FRAGMENT),10)
    from panda3d.core import BitMask32
    node.hide(BitMask32.bit(2))
    node.set_shader_input("water_color",effects.water_color)
    node.set_shader_input("sky_color",effects.fog_color)
    node.set_shader_input("fog_density",effects.fog_density)
    node.set_shader_input("absorption",effects.water_absorption)
    node.set_shader_input("foam_strength",effects.water_foam)
    node.set_shader_input("nearp",.05);node.set_shader_input("farp",5000.)
    fallback=Texture("water-fallback")
    fallback.setup_2d_texture(1,1,Texture.T_unsigned_byte,Texture.F_rgba8)
    fallback.set_ram_image_as(bytes((0,0,0,255)),"RGBA")
    for name in ("reflection_tex","refraction_tex","refraction_depth"):node.set_shader_input(name,fallback)
    for name in ("use_reflection","use_refraction"):node.set_shader_input(name,0.)
    return node
