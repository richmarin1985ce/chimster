"""Optional upstream Panda post-processing adapters.

Only one filter graph owns the output at a time. No ShowBase or main loop.
SimplePBR's private cleanup/update methods are scoped to the pinned release.
"""
class ManualTasks:
    def __init__(self):self.callback=None
    def add(self,callback,name,sort=0):self.callback=callback
    def remove(self,*args):self.callback=None
    def step(self):
        if self.callback is not None:
            from direct.task.Task import Task
            self.callback(Task())

class PBR:
    def __init__(self,preview,effects):
        import simplepbr
        self.preview=preview;self.tasks=ManualTasks();self.volume_post=None;self.cascades=None
        # Use the preview's own engine, not the global ShowBase engine.
        class Pipeline(simplepbr.Pipeline):
            def get_all_casters(self):
                return [n.node() for n in (preview.sun,*preview.effect_nodes) if hasattr(n.node(),"is_shadow_caster") and n.node().is_shadow_caster()]
        self.state=preview.root.get_state()
        self.pipeline=Pipeline.__new__(Pipeline)
        try:
            from .panda_volume import needs_volume
            volume=needs_volume(effects)
            env=None
            if effects.environment_strength:
                from .panda_environment import environment
                env=environment(tuple(effects.fog_color),effects.environment_strength)
            self.pipeline.__init__(env_map=env,render_node=preview.root,window=preview.output,camera_node=preview.camera,taskmgr=self.tasks,msaa_samples=0,max_lights=6,use_normal_maps=True,use_occlusion_maps=True,enable_fog=bool(effects.fog_density) and not volume,enable_hardware_skinning=False,use_330=True,shadow_bias=effects.shadow_bias)
            self.pipeline.verify_shaders()
            if effects.shadow_size and effects.shadow_cascades==2:
                from .panda_cascades import Cascades,shader
                from panda3d.core import ShaderAttrib
                self.cascades=Cascades(preview,effects)
                preview.root.set_shader(shader(self.pipeline))
                self.pipeline._set_env_map_uniforms()
                preview.root.set_shader_input("global_shadow_bias",effects.shadow_bias)
                self.cascades.update();self.cascades.bind(preview.root)
                self.pipeline.verify_shaders()
            if volume or effects.ao_strength:
                from .panda_glsl_filters import GLSLFilters
                self.volume_post=GLSLFilters(preview,effects,pipeline=self.pipeline,cascades=self.cascades)
        except Exception:
            self.close()
            raise
    @property
    def shadow_error(self):return self.volume_post.shadow_error if self.volume_post is not None else None
    def update(self):
        self.tasks.step()
        if self.cascades is not None:self.cascades.update();self.cascades.bind(self.preview.root)
        if self.volume_post is not None:self.volume_post.update()
    def close(self):
        if self.volume_post is not None:self.volume_post.close();self.volume_post=None
        if self.cascades is not None:self.cascades.close();self.cascades=None
        self.tasks.remove()
        mgr=getattr(self.pipeline,"_filtermgr",None)
        if mgr is not None:
            mgr.cleanup();mgr.ignore_all()
        self.preview.root.set_state(self.state)

class NativeFilters:
    def __init__(self,preview,effects):
        from direct.filter.CommonFilters import CommonFilters
        self.preview=preview
        self.state=preview.root.get_state()
        self.filters=CommonFilters(preview.output,preview.camera)
        self.caster=None
        try:
            preview.root.set_shader_auto()
            if effects.ao_strength:
                if not self.filters.setAmbientOcclusion(numsamples=16,amount=2*effects.ao_strength,radius=.05):
                    raise RuntimeError("Native SSAO unavailable")
            if effects.scatter_strength:
                self.caster=preview.root.attach_new_node("sun-shaft-anchor")
                self.caster.set_pos(preview.sun.get_pos())
                if not self.filters.setVolumetricLighting(self.caster,numsamples=effects.volume_steps,density=.75,decay=.96,exposure=.08*effects.scatter_strength):
                    raise RuntimeError("Native light shafts unavailable")
            if self.filters.finalQuad is not None:
                shader=self.filters.finalQuad.get_shader()
                if shader is None:raise RuntimeError("Native filters shader unavailable")
                gsg=preview.output.get_gsg()
                shader.prepare_now(gsg.get_prepared_objects(),gsg)
                if shader.get_error_flag():raise RuntimeError("Native filter shader compilation failed")
        except Exception:
            self.close()
            raise
    def update(self):
        if self.caster is not None:self.caster.set_pos(self.preview.sun.get_pos())
        if self.filters.finalQuad is not None:self.filters.update()
    def close(self):
        self.filters.cleanup();self.filters.manager.ignore_all()
        if self.caster is not None:self.caster.remove_node();self.caster=None
        self.preview.root.set_state(self.state)
