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
        self.preview=preview;self.tasks=ManualTasks()
        # Use the preview's own engine, not the global ShowBase engine.
        class Pipeline(simplepbr.Pipeline):
            def get_all_casters(self):
                return [n.node() for n in (preview.sun,*preview.effect_nodes) if hasattr(n.node(),"is_shadow_caster") and n.node().is_shadow_caster()]
        self.state=preview.root.get_state()
        self.pipeline=Pipeline.__new__(Pipeline)
        try:
            self.pipeline.__init__(render_node=preview.root,window=preview.output,camera_node=preview.camera,taskmgr=self.tasks,msaa_samples=0,max_lights=6,use_normal_maps=True,use_occlusion_maps=True,enable_fog=bool(effects.fog_density),enable_hardware_skinning=False,use_330=True,shadow_bias=effects.shadow_bias)
            self.pipeline.verify_shaders()
        except Exception:
            self.close()
            raise
    def update(self):
        self.tasks.step()
    def close(self):
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
        try:
            preview.root.set_shader_auto()
            if effects.ao_strength:
                if not self.filters.setAmbientOcclusion(numsamples=16,amount=2*effects.ao_strength,radius=.05):
                    raise RuntimeError("Native SSAO unavailable")
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
        if self.filters.finalQuad is not None:self.filters.update()
    def close(self):
        self.filters.cleanup();self.filters.manager.ignore_all()
        self.preview.root.set_state(self.state)
