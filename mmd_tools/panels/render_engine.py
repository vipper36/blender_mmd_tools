# -*- coding: utf-8 -*-

import bpy, math

class MMDToolsRenderEngine(bpy.types.RenderEngine):
	bl_idname = 'mmd_tools_engine'
	bl_label = 'mmd_tools Engine'

# https://www.blender.org/api/blender_python_api_2_76_9/bpy.types.RenderEngine.html
	bl_use_preview = True
	# bl_use_shading_nodes = False
	# bl_use_game_engine = True
	bl_use_internal_engine = True
	bl_use_native_node_tree = True
	# bl_use_postprocess

mmdtools_compat_panels = [

	"DATA_PT_context_speaker",
	"WORLD_PT_context_world",
	"MATERIAL_PT_context_material",
	"DATA_PT_context_camera",
	"DATA_PT_context_lamp",
	"DATA_PT_context_mesh",

	"RENDER_PT_render",
	"MATERIAL_PT_preview",

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

	# Lock Camera to View like MMD
	bpy.context.space_data.lock_camera = True
	if bpy.context.space_data.region_3d.view_perspective != "CAMERA":
		bpy.ops.view3d.viewnumpad(type='CAMERA', align_active=False)
	bpy.context.space_data.region_3d.view_camera_zoom = 1

	# disable color management (scene side)
	active_scene.display_settings.display_device = 'None'
	active_scene.view_settings.view_transform = 'Default'
	active_scene.view_settings.exposure = 0.0
	active_scene.view_settings.gamma = 1.0
	active_scene.view_settings.look = 'None'
	active_scene.view_settings.use_curve_mapping = False
	active_scene.sequencer_colorspace_settings.name = 'Linear'

	# テクスチャ側
	# disable color management (texture side)
	# bpy.data.images["Untitled"].colorspace_settings.name = 'Linear'

	# mmd compat background
	world = bpy.context.scene.world
	if not world:
		world = bpy.context.scene.world = bpy.data.worlds.new("World")
	world.horizon_color = (1, 1, 1)
	world.ambient_color = (0, 0, 0)
	bpy.context.space_data.show_world = True

	# mmd compat screen
	active_scene.render.resolution_x = 512
	active_scene.render.resolution_y = 288
	active_scene.render.resolution_percentage = 100

	# mmd compat camera
	tgt = bpy.data.objects.new( "Cam_Target", None )
	active_scene.objects.link( tgt )

	tgt.location = (0, 0, 10)

	tgt.empty_draw_size = 1
	tgt.empty_draw_type = 'CIRCLE'
	tgt.hide_select = True

#	tgt_look_at = tgt.constraints.new(type='TRACK_TO')
#	tgt_look_at.target = bpy.context.scene.camera
#	tgt_look_at.up_axis = 'UP_X'
#	tgt_look_at.track_axis = 'TRACK_Y'

	# TODO: prevent dup setting

	camera = bpy.context.scene.camera
	if not camera:
		camera_in = bpy.data.cameras.new("Camera")
		camera = bpy.data.objects.new("Camera", camera_in)
		active_scene.objects.link(camera)

	camera.location = (0, -45, 10)

	camera_look_at = camera.constraints.new(type='TRACK_TO')
	camera_look_at.target = tgt
	camera_look_at.up_axis = 'UP_Y'
	camera_look_at.track_axis = 'TRACK_NEGATIVE_Z'

	# set 30 degree short-side FOV
	# TODO: not good for portrait
	camera.data.sensor_fit = 'VERTICAL'
	camera.data.lens_unit = 'FOV'
	camera.data.angle = 0.523599 # deg2rad(30)

	camera.data.clip_end = 1000

def mmd_tools_panel_init_menu_draw(self, context):
	self.layout.operator("mmd_tools.init_scene")

class MMDToolsInitScene(bpy.types.Operator):
	"""Set MMD default parameter to current Scene"""
	bl_idname = "mmd_tools.init_scene"
	bl_label = "Init MMD Scene"
	bl_options = {'REGISTER'}

	def execute(self, context):
		mmd_tools_scene_init()

		return {'FINISHED'}

def register():
	bpy.utils.register_class(MMDToolsRenderEngine)

	for cp in mmdtools_compat_panels:
		if hasattr(bpy.types, cp):
			panel = getattr(bpy.types, cp)
			panel.COMPAT_ENGINES.add('mmd_tools_engine')

	bpy.utils.register_class(MMDToolsInitScene)
	bpy.types.OBJECT_PT_mmd_tools_object.append(mmd_tools_panel_init_menu_draw)

def unregister():

	bpy.types.OBJECT_PT_mmd_tools_object.remove(mmd_tools_panel_init_menu_draw)
	bpy.utils.unregister_class(MMDToolsInitScene)

	for cp in mmdtools_compat_panels:
		if hasattr(bpy.types, cp):
			panel = getattr(bpy.types, cp)
			panel.COMPAT_ENGINES.remove('mmd_tools_engine')

	bpy.utils.unregister_class(MMDToolsRenderEngine)

if __name__ == "__main__":
	register()
