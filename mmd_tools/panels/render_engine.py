# -*- coding: utf-8 -*-

import bpy, math

class MMDToolsRenderEngine(bpy.types.RenderEngine):
	bl_idname = 'MMD_TOOLS_ENGINE'
	bl_label = 'mmd_tools Engine'

# https://www.blender.org/api/blender_python_api_2_76_9/bpy.types.RenderEngine.html
	bl_use_preview = True
	# bl_use_shading_nodes_custom = False # for debug
	# bl_use_shading_nodes = True
	# bl_use_game_engine = True
	bl_use_save_buffers = True
	bl_use_internal_engine = True
	# bl_use_postprocess

mmdtools_compat_panels = [

	"DATA_PT_context_speaker",
	"WORLD_PT_context_world",
#	"MATERIAL_PT_context_material", # for debug
	"DATA_PT_context_camera",
	"DATA_PT_context_lamp",
	"DATA_PT_context_mesh",

	"RENDER_PT_render",
#	"MATERIAL_PT_preview",

	"CAMERA_MT_presets",
	"SAFE_AREAS_MT_presets",
	"DATA_PT_lens",
	"DATA_PT_camera",
	"DATA_PT_camera_dof",
	"DATA_PT_camera_display",
	"DATA_PT_camera_safe_areas",

	"LAMP_MT_sunsky_presets",
	"DATA_PT_preview",
	"DATA_PT_lamp",
	"DATA_PT_sunsky",
	"DATA_PT_shadow",
	"DATA_PT_area",
	"DATA_PT_spot",
	"DATA_PT_falloff_curve",

	"MESH_MT_vertex_group_specials",
	"MESH_MT_shape_key_specials",

	"DATA_PT_normals",
	"DATA_PT_texture_space",
	"DATA_PT_vertex_groups",
	"DATA_PT_shape_keys",
	"DATA_PT_uv_texture",
	"DATA_PT_vertex_colors",
	"DATA_PT_customdata",

	"DATA_PT_speaker",
	"DATA_PT_distance",
	"DATA_PT_cone",


	"RENDER_PT_dimensions",
	"RENDER_PT_output",
	"RENDER_PT_encoding",
	"RENDER_PT_antialiasing",

	"SCENE_PT_keying_sets",
	"SCENE_PT_keying_set_paths",

	"SCENE_PT_keying_sets",
	"SCENE_PT_keying_set_paths",

	"SCENE_PT_scene",
	"SCENE_PT_audio",
	"WORLD_PT_preview",
	"WORLD_PT_world",
]

def mmd_tools_scene_init():
	active_scene = bpy.context.scene
	active_unit = active_scene.unit_settings

	# set mikucell unit
	active_unit.system = 'METRIC'
	active_unit.system_rotation = 'DEGREES'
	active_unit.scale_length = 0.08
	active_unit.use_separate = False

	bpy.context.space_data.grid_scale = 0.4
	bpy.context.space_data.grid_lines = 20

	# Show all axis like MMD
	bpy.context.space_data.show_axis_x = True
	bpy.context.space_data.show_axis_y = True
	bpy.context.space_data.show_axis_z = True

	# disable color management (scene side)
	active_scene.display_settings.display_device = 'None'
	active_scene.view_settings.view_transform = 'Default'
	active_scene.view_settings.exposure = 0.0
	active_scene.view_settings.gamma = 1.0
	active_scene.view_settings.look = 'None'
	active_scene.view_settings.use_curve_mapping = False
	active_scene.sequencer_colorspace_settings.name = 'Linear'

	# disable color management (texture side)
	# bpy.data.images["Untitled"].colorspace_settings.name = 'Linear'

	# mmd compat background
	world = bpy.context.scene.world
	if not world:
		world = bpy.context.scene.world = bpy.data.worlds.new("World")
	world.horizon_color = (1, 1, 1)
	world.ambient_color = (0, 0, 0)
	world.exposure = 0.0

	bpy.context.space_data.show_world = True

	# mmd compat screen
	active_scene.render.resolution_x = 512
	active_scene.render.resolution_y = 288
	active_scene.render.resolution_percentage = 100

	# mmd compat camera

	# TODO: prevent dup setting

	camera = bpy.context.scene.camera
	if not camera:
		camera_in = bpy.data.cameras.new("Camera")
		camera = bpy.data.objects.new("Camera", camera_in)
		active_scene.objects.link(camera)

	# set 30 degree short-side FOV
	# TODO: not good for portrait
	camera.data.sensor_fit = 'VERTICAL'
	camera.data.lens_unit = 'FOV'
	camera.data.angle = 0.523599 # deg2rad(30)

	camera.data.clip_end = 1000

	camera.data.passepartout_alpha = 1 # just for style

	camera.location = (0, -45, 10)
	camera.rotation_mode = 'XYZ'
	camera.rotation_euler = (1.5708, 0.0, 0.0)

	tgt_data = bpy.data.meshes.new("Cam_Target")

	tgt = bpy.data.objects.new( "Cam_Target", tgt_data )
	active_scene.objects.link( tgt )


	bpy.ops.object.select_all(action='DESELECT')
	tgt.select = True
	bpy.context.scene.objects.active = tgt

	bpy.ops.object.mode_set(mode='EDIT')
	bpy.ops.mesh.primitive_circle_add(vertices=64, radius=0.35, location=(0, 0, 0), rotation=(0, 0, 0))
	bpy.ops.mesh.extrude_region()
	bpy.ops.transform.resize(value=(0.75, 0.75, 0.75))
	bpy.ops.mesh.primitive_circle_add(vertices=64, radius=0.2, location=(0, 0, 0), rotation=(0, 0, 0))
	bpy.ops.mesh.edge_face_add()
	bpy.ops.object.mode_set(mode='OBJECT')

	tgt_mat = bpy.data.materials.new(name="mmd_tools Cam Target")
	tgt_mat.use_shadeless = True
	tgt_mat.diffuse_color = (0.929412, 0.0784314, 0.356863)
	tgt_mat.game_settings.use_backface_culling = False
	tgt_data.materials.append(tgt_mat)
	tgt.show_x_ray = True

	tgt.parent = camera

	tgt.rotation_euler = (0.0, 0.0, 0.0)
	tgt.location = (0, 0, -45)


	# Lock Camera to View like MMD
	bpy.context.space_data.lock_camera = True
	if bpy.context.space_data.region_3d.view_perspective != "CAMERA":
		bpy.ops.view3d.viewnumpad(type='CAMERA', align_active=False)
	bpy.context.space_data.region_3d.view_camera_zoom = 1

	tgt.select = False
	camera.select = True
	bpy.context.scene.objects.active = camera
	tgt.hide_select = True
	tgt.hide_render = True

	# MMD-compat lamp
	lamp_in = bpy.data.lamps.new(name="MMD_Lamp", type="SUN")
	lamp_in.color = (154/255.0, 154/255.0, 154/255.0)
	lamp_in.energy = 1.0
	lamp_in.shadow_method = 'RAY_SHADOW'
	lamp = bpy.data.objects.new(name="MMD_Lamp", object_data=lamp_in)
	lamp.location = (0.0, 0.0, 0.0)
	active_scene.objects.link(lamp)
	lamp.hide = True

	lamp_tgt = bpy.data.objects.new( "LAMP_Target", None )
	active_scene.objects.link( lamp_tgt )
	lamp_tgt.location = (0, 0, 0)
	lamp_tgt.hide_select = True
	lamp_tgt.hide = True
	lamp_tgt.hide_render = True

	lamp_look_at = lamp.constraints.new(type='TRACK_TO')
	lamp_look_at.target = lamp_tgt
	lamp_look_at.up_axis = 'UP_X'
	lamp_look_at.track_axis = 'TRACK_NEGATIVE_Z'

	# for ground
	glamp_in = bpy.data.lamps.new(name="MMD_Lamp_Ground", type="SPOT")
	glamp_in.energy = 1.0
	glamp_in.falloff_type = 'CONSTANT'
	glamp_in.shadow_method = 'BUFFER_SHADOW'
	glamp_in.use_only_shadow = True
	glamp_in.shadow_color = (1.0, 1.0, 1.0) # important
#	glamp_in.shadow_buffer_type = 'HALFWAY'
#	glamp_in.shadow_sample_buffers = 'BUFFERS_4'
#	glamp_in.shadow_buffer_size = 1024
	glamp_in.shadow_buffer_type = 'IRREGULAR'
	glamp_in.shadow_buffer_bias = 0.1 # ???
	glamp_in.use_auto_clip_start = True
	glamp_in.shadow_buffer_clip_end = 9999
	glamp_in.spot_size = 0.0349066 # 2d
	glamp_in.spot_blend = 0
	glamp = bpy.data.objects.new(name="MMD_Lamp_Ground", object_data=glamp_in)

	active_scene.objects.link(glamp)
	glamp.parent = lamp
	glamp.location = (0.0, 0.0, 4999.0) #(0.5 * 5000, -0.5 * 5000, 1.0 * 5000)

	glamp_look_at = glamp.constraints.new(type='TRACK_TO')
	glamp_look_at.target = lamp_tgt
	glamp_look_at.up_axis = 'UP_X'
	glamp_look_at.track_axis = 'TRACK_NEGATIVE_Z'

	glamp.hide = True

	lamp.location = (0.5, -0.5, 1.0)

	lamp_group = bpy.data.groups.new("MMD_Lamp_Ground")
	lamp_group.objects.link(glamp)

	shadow_catcher_mat_base = bpy.data.materials.new(name="mmd_tools Shadow Catcher Base")
	shadow_catcher_mat_base.use_only_shadow = True
	shadow_catcher_mat_base.use_shadows = True
	shadow_catcher_mat_base.use_transparent_shadows = True # False in MMD but who cares?
	shadow_catcher_mat_base.shadow_only_type = 'SHADOW_ONLY'
	shadow_catcher_mat_base.light_group = lamp_group

	shadow_catcher_mat = bpy.data.materials.new(name="mmd_tools Shadow Catcher")
	shadow_catcher_mat.use_nodes = True
	shadow_catcher_mat.use_transparency = True
	nodes = shadow_catcher_mat.node_tree.nodes
	nodes["Material"].material = shadow_catcher_mat_base
	nodes["Material"].inputs[0].default_value = [1.0, 1.0, 1.0, 1.0]
	nodes["Material"].inputs[1].default_value = [0.0, 0.0, 0.0, 1.0]
	nodes["Material"].inputs[2].default_value = 1.0
	nodes["Material"].inputs[3].default_value = [0.0, 0.0, 0.0]
	nodes["Material"].use_specular = False

	cmn = nodes.new("ShaderNodeMixRGB")
	shadow_catcher_mat.node_tree.links.new(cmn.inputs[0], nodes["Material"].outputs[1])
	cmn.inputs[1].default_value = [1.0, 1.0, 1.0, 1.0]
	cmn.inputs[2].default_value = [(87 / 255) * (1.0/0.6), (87 / 255) * (1.0/0.6), (87 / 255) * (1.0/0.6), 1.0] # checked
	cmn.blend_type = 'MULTIPLY'
	shadow_catcher_mat.node_tree.links.new(nodes["Output"].inputs[0], cmn.outputs[0])
	nodes["Output"].inputs[1].default_value = 0.6 # checked

	shadow_catcher_in = bpy.data.meshes.new("Shadow_Catcher_Mesh")

	verts = [(-500.0, 500.0, 0.0), (-500.0, -500.0, 0.0), (500.0, -500.0, 0.0), (500.0, 500.0, 0.0)]
	shadow_catcher_in.from_pydata(verts, [], [[0,1,2,3]])
	shadow_catcher_in.update(calc_edges=True)
	shadow_catcher_in.materials.append(shadow_catcher_mat)

	shadow_catcher = bpy.data.objects.new( "Shadow_Catcher", shadow_catcher_in )
	shadow_catcher.location = (0.0, 0.0, 0.0)

	shadow_catcher.hide_select = True
	shadow_catcher.hide = True

	active_scene.objects.link(shadow_catcher)

	bpy.context.scene.world.mmd_shadow_catcher = shadow_catcher.name

	bpy.context.area.spaces[0].viewport_shade='TEXTURED'
	bpy.context.scene.game_settings.material_mode = 'GLSL'

	bpy.context.space_data.show_backface_culling = True # for non-GLSL shader

def mmd_tools_scene_create():
	bpy.ops.scene.new(type="NEW")
	scene = bpy.context.scene
	scene.name = "MMD Scene"
	scene.render.engine = "MMD_TOOLS_ENGINE"
	mmd_tools_scene_init()

#class MMDToolsInitScene(bpy.types.Operator):
#	"""Set MMD default parameter to current Scene"""
#	bl_idname = "mmd_tools.init_scene"
#	bl_label = "Init MMD Scene"
#	bl_options = {'REGISTER'}
#
#	def execute(self, context):
#		mmd_tools_scene_init()
#
#		return {'FINISHED'}

 # XXX: should move to operators
class MMDToolsCreateScene(bpy.types.Operator):
	"""Create a scene with MMD default params"""
	bl_idname = "mmd_tools.create_scene"
	bl_label = "Create MMD Scene"
	bl_options = {'REGISTER'}

	def execute(self, context):
		mmd_tools_scene_create()

		return {'FINISHED'}

def mmdtools_engine_add():
	for cp in mmdtools_compat_panels:
		if hasattr(bpy.types, cp):
			panel = getattr(bpy.types, cp)
			panel.COMPAT_ENGINES.add('MMD_TOOLS_ENGINE')

def mmdtools_engine_remove():
	for cp in mmdtools_compat_panels:
		if hasattr(bpy.types, cp):
			panel = getattr(bpy.types, cp)
			panel.COMPAT_ENGINES.remove('MMD_TOOLS_ENGINE')

