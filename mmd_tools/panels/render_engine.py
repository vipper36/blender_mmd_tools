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

def mmd_tools_engine_shader_create():
	groups = bpy.data.node_groups
	if "mmd_tools_shader" in groups:
		return groups["mmd_tools_shader"]
	mat = bpy.data.materials.new(name="mmd_tools Node Base")

	# light color receiver hack!
	l_mat = bpy.data.materials.new(name="mmd_tools Light Base")
	l_mat.diffuse_shader = 'FRESNEL'
	l_mat.diffuse_fresnel = 0.0
	l_mat.diffuse_fresnel_factor = 0.0
	l_mat.use_shadows = False

	# type, input, params, name
	engine_shader = [
		["NodeGroupInput", None, None, "mmd_tools Group Input"],

		["ShaderNodeExtendedMaterial", [
			[1.0, 1.0, 1.0, 1.0],
			[0.0, 0.0, 0.0, 1.0],
			1.0,
			[0.0, 0.0, 0.0],
			[0.0, 0.0, 0.0, 1.0],
			1.0,
			0.0,
			1.0,
			0.0,
			1.0,
			0.0,
		], {
			"use_diffuse": True,
			"use_specular": False,
			"invert_normal": False,
			"material": bpy.data.materials["mmd_tools Light Base"]},
			"mmd_tools Lamp Data"],

		["ShaderNodeMixRGB",[
			1.0,
			["mmd_tools Lamp Data", 0],
			[0.2, 0.2, 0.2, 1.0], # 1/energy
		],
		{"blend_type": "MULTIPLY", "use_clamp": True}, "mmd_tools Lamp Color"],

		["ShaderNodeMixRGB",[
			1.0,
			["mmd_tools Lamp Color", 0],
			["mmd_tools Group Input", 0],
		],
		{"blend_type": "MULTIPLY", "use_clamp": True}, "mmd_tools Dif Mul"],


		["ShaderNodeMixRGB",[
			1.0,
			["mmd_tools Group Input", 1],
			["mmd_tools Group Input", 2],
		],
		{"blend_type": "MULTIPLY", "use_clamp": True}, "mmd_tools Spec Mul"],

		["ShaderNodeMixRGB",[
			1.0,
			["mmd_tools Dif Mul", 0],
			["mmd_tools Spec Mul", 0],
		],
		{"blend_type": "ADD", "use_clamp": True}, "mmd_tools Spec Add"],

		["ShaderNodeMixRGB",[
			1.0,
			["mmd_tools Spec Add", 0],
			["mmd_tools Group Input", 3],
		],
		{"blend_type": "ADD", "use_clamp": True}, "mmd_tools Amb Add"],

		["ShaderNodeMixRGB",[
			1.0,
			["mmd_tools Amb Add", 0],
			["mmd_tools Group Input", 4],
		],
		{"blend_type": "MULTIPLY", "use_clamp": True}, "mmd_tools Tex Mul"],

# TOON
		["ShaderNodeExtendedMaterial", [
			[1.0, 1.0, 1.0, 1.0],
			[0.0, 0.0, 0.0, 1.0],
			1.0,
			[0.0, 0.0, 0.0],
			[0.0, 0.0, 0.0, 1.0],
			1.0,
			0.0,
			1.0,
			0.0,
			1.0,
			0.0,
		], {
			"use_diffuse": True,
			"use_specular": True,
			"invert_normal": False,
			"material": bpy.data.materials["mmd_tools Node Base"]},
			"mmd_tools Pure Material"],

		["ShaderNodeValToRGB",[["mmd_tools Pure Material", 0]], None, "mmd_tools ToonRamp 1"],
		["ShaderNodeValToRGB",[["mmd_tools Pure Material", 0]], None, "mmd_tools ToonRamp 2"],
		["ShaderNodeValToRGB",[["mmd_tools Pure Material", 0]], None, "mmd_tools ToonRamp 3"],
		["ShaderNodeValToRGB",[["mmd_tools Pure Material", 0]], None, "mmd_tools ToonRamp 4"],
		["ShaderNodeValToRGB",[["mmd_tools Pure Material", 0]], None, "mmd_tools ToonRamp 5"],
		["ShaderNodeValToRGB",[["mmd_tools Pure Material", 0]], None, "mmd_tools ToonRamp 6"],

		["ShaderNodeMath",[
			["mmd_tools Group Input", 5],
			-0.1, #XXX
		], {"operation": "GREATER_THAN"}, "mmd_tools Math 1"],
		["ShaderNodeMath",[
			["mmd_tools Group Input", 5],
			0.9,
		], {"operation": "GREATER_THAN"}, "mmd_tools Math 2"],
		["ShaderNodeMath",[
			["mmd_tools Group Input", 5],
			1.9,
		], {"operation": "GREATER_THAN"}, "mmd_tools Math 3"],
		["ShaderNodeMath",[
			["mmd_tools Group Input", 5],
			2.9,
		], {"operation": "GREATER_THAN"} , "mmd_tools Math 4"],
		["ShaderNodeMath",[
			["mmd_tools Group Input", 5],
			3.9,
		], {"operation": "GREATER_THAN"} , "mmd_tools Math 5"],
		["ShaderNodeMath",[
			["mmd_tools Group Input", 5],
			4.9,
		], {"operation": "GREATER_THAN"} , "mmd_tools Math 6"],
		["ShaderNodeMath",[
			["mmd_tools Group Input", 5],
			5.9,
		], {"operation": "GREATER_THAN"}, "mmd_tools Math 7"],

		["ShaderNodeMixRGB",[
			["mmd_tools Math 1", 0],
			["mmd_tools Pure Material", 0],
			["mmd_tools ToonRamp 1", 0],
		], None, "mmd_tools Mix 1"],
		["ShaderNodeMixRGB",[
			["mmd_tools Math 2", 0],
			["mmd_tools Mix 1", 0],
			["mmd_tools ToonRamp 2", 0],
		], None, "mmd_tools Mix 2"],
		["ShaderNodeMixRGB",[
			["mmd_tools Math 3", 0],
			["mmd_tools Mix 2", 0],
			["mmd_tools ToonRamp 3", 0],
		], None, "mmd_tools Mix 3"],
		["ShaderNodeMixRGB",[
			["mmd_tools Math 4", 0],
			["mmd_tools Mix 3", 0],
			["mmd_tools ToonRamp 4", 0],
		], None, "mmd_tools Mix 4"],
		["ShaderNodeMixRGB",[
			["mmd_tools Math 5", 0],
			["mmd_tools Mix 4", 0],
			["mmd_tools ToonRamp 5", 0],
		], None, "mmd_tools Mix 5"],
		["ShaderNodeMixRGB",[
			["mmd_tools Math 6", 0],
			["mmd_tools Mix 5", 0],
			["mmd_tools ToonRamp 6", 0],
		], None, "mmd_tools Mix 6"],
		["ShaderNodeMixRGB",[
			["mmd_tools Math 7", 0],
			["mmd_tools Mix 6", 0],
			["mmd_tools Pure Material", 0],
		], None, "mmd_tools Mix 7"],

		["ShaderNodeMixRGB",[
			1.0,
			["mmd_tools Tex Mul", 0],
			["mmd_tools Mix 7", 0],
		],
		{"blend_type": "MULTIPLY", "use_clamp": True}, "mmd_tools Mul"],
	# ["ShaderNodeOutput", [["mmd_tools Add", 0], 1.0], None, "mmd_tools Output"],
	# ["ShaderNodeRGB", , , ],
		["NodeGroupOutput", [["mmd_tools Mul", 0]], None,
			"mmd_tools Group Output"],
]


	shader = groups.new(name='mmd_tools_shader', type='ShaderNodeTree')
	nodes = shader.nodes

	for n in engine_shader:
		node = nodes.new(n[0])
		node.name = n[3]

		# should set material before diffuse intensity
		if n[2] is not None:
			for k in n[2]:
				setattr(node, k, n[2][k])

		if n[1] is not None:
			for i, x in enumerate(n[1]):
				if type(x) is list and type(x[0]) is str:
					shader.links.new(node.inputs[i], nodes[x[0]].outputs[x[1]])
					continue

				node.inputs[i].default_value = x



	color_ramp = nodes["mmd_tools ToonRamp 1"].color_ramp
	color_ramp.interpolation = "CONSTANT"
	color_ramp.elements[0].position = 0.0
	color_ramp.elements[0].color = (0.803922, 0.803922, 0.803922, 1.0)
	color_ramp.elements[1].position = 0.5
	color_ramp.elements[1].color = (1.0, 1.0, 1.0, 1.0)

	color_ramp = nodes["mmd_tools ToonRamp 2"].color_ramp
	color_ramp.interpolation = "CONSTANT"
	color_ramp.elements[0].position = 0.0
	color_ramp.elements[0].color = (0.960784, 0.882353, 0.882353, 1.0)
	color_ramp.elements[1].position = 0.5
	color_ramp.elements[1].color = (1.0, 1.0, 1.0, 1.0)

	color_ramp = nodes["mmd_tools ToonRamp 3"].color_ramp
	color_ramp.interpolation = "CONSTANT"
	color_ramp.elements[0].position = 0.0
	color_ramp.elements[0].color = (0.603922, 0.603922, 0.603922, 1.0)
	color_ramp.elements[1].position = 0.5
	color_ramp.elements[1].color = (1.0, 1.0, 1.0, 1.0)

	color_ramp = nodes["mmd_tools ToonRamp 4"].color_ramp
	color_ramp.interpolation = "CONSTANT"
	color_ramp.elements[0].position = 0.0
	color_ramp.elements[0].color = (0.972549, 0.937255, 0.921569, 1.0)
	color_ramp.elements[1].position = 0.5
	color_ramp.elements[1].color = (1.0, 1.0, 1.0, 1.0)

	# XXX: not accurate
	color_ramp = nodes["mmd_tools ToonRamp 5"].color_ramp
	color_ramp.interpolation = "EASE"
	color_ramp.elements[0].position = 0.25
	color_ramp.elements[0].color = (1.0, 0.905882, 0.870588, 1.0)
	color_ramp.elements[1].position = 0.5
	color_ramp.elements[1].color = (1.0, 1.0, 1.0, 1.0)

	# XXX: not accurate
	color_ramp = nodes["mmd_tools ToonRamp 6"].color_ramp
	color_ramp.interpolation = "EASE"
	color_ramp.elements[0].position = 0.25 - (1.0/32.0)
	color_ramp.elements[0].color = (0.764706, 0.67451, 0.0117647, 1.0)
	color_ramp.elements[1].position = 0.25 + (1.0/32.0)
	color_ramp.elements[1].color = (1.0, 0.929412, 0.380392, 1.0)
	color_ramp.elements.new(0.75 - (1.5/32.0))
	color_ramp.elements[2].color = (1.0, 0.929412, 0.380392, 1.0)
	color_ramp.elements.new(0.75)
	color_ramp.elements[3].color = (1.0, 0.996078, 0.94902, 1.0)
	color_ramp.elements.new(0.75 + (1.5/32.0))
	color_ramp.elements[4].color = (1.0, 0.929412, 0.380392, 1.0)

	shader.inputs[0].name = "Dif"
	shader.inputs[0].default_value = [1.0, 1.0, 1.0, 1.0]
	shader.inputs[1].name = "Spec"
	shader.inputs[1].default_value = [1.0, 1.0, 1.0, 1.0]
	shader.inputs[2].name = "Spec Weight"
	shader.inputs[2].default_value = [1.0, 1.0, 1.0, 1.0]
	shader.inputs[3].name = "Amb"
	shader.inputs[3].default_value = [0.0, 0.0, 0.0, 1.0]
	shader.inputs[4].name = "Tex"
	shader.inputs[4].default_value = [1.0, 1.0, 1.0, 1.0]
	shader.inputs[5].name = "Toon"
	shader.inputs[5].default_value = 0.0

	return shader


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

	camera.data.passepartout_alpha = 1 # just for style

	# Lock Camera to View like MMD
	bpy.context.space_data.lock_camera = True
	if bpy.context.space_data.region_3d.view_perspective != "CAMERA":
		bpy.ops.view3d.viewnumpad(type='CAMERA', align_active=False)
	bpy.context.space_data.region_3d.view_camera_zoom = 1

	# MMD-compat lamp
	lamp_in = bpy.data.lamps.new(name="MMD_Lamp", type="SUN")
	lamp_in.color = (154/255.0, 154/255.0, 154/255.0)
	lamp_in.energy = 5.0 # XXX: why?
	lamp_in.shadow_method = 'RAY_SHADOW'
	lamp = bpy.data.objects.new(name="MMD_Lamp", object_data=lamp_in)
	lamp.location = (0.5, -0.5, 1.0)
	active_scene.objects.link(lamp)

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

	shadow_catcher_mat = bpy.data.materials.new(name="mmd_tools Shadow Catcher")
	shadow_catcher_mat.use_only_shadow = True
	shadow_catcher_mat.shadow_only_type = 'SHADOW_ONLY'

	# XXX: I have no idea if this is good or bad.
	shadow_catcher_mat.use_transparency = True
	shadow_catcher_mat.alpha = 0.3

	shadow_catcher_in = bpy.data.meshes.new("Shadow_Catcher_Mesh")

	verts = [(-50.0, 50.0, 0.0), (-50.0, -50.0, 0.0), (50.0, -50.0, 0.0), (50.0, 50.0, 0.0)]
	shadow_catcher_in.from_pydata(verts, [], [[0,1,2,3]])
	shadow_catcher_in.update(calc_edges=True)
	shadow_catcher_in.materials.append(shadow_catcher_mat)

	shadow_catcher = bpy.data.objects.new( "Shadow_Catcher", shadow_catcher_in )
	shadow_catcher.location = (0.0, 0.0, 0.0)

	shadow_catcher.hide_select = True
	shadow_catcher.hide = True

	active_scene.objects.link(shadow_catcher)

	# MMD-compat shader (WIP)
	mmd_tools_engine_shader_create()

	bpy.context.area.spaces[0].viewport_shade='TEXTURED'
	bpy.context.scene.game_settings.material_mode = 'GLSL'

def mmd_tools_scene_create():
	bpy.ops.scene.new(type="NEW")
	scene = bpy.context.scene
	scene.name = "MMD Scene"
	scene.render.engine = "mmd_tools_engine"
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
			panel.COMPAT_ENGINES.add('mmd_tools_engine')

def mmdtools_engine_remove():
	for cp in mmdtools_compat_panels:
		if hasattr(bpy.types, cp):
			panel = getattr(bpy.types, cp)
			panel.COMPAT_ENGINES.remove('mmd_tools_engine')


# for debug
#def mmd_tools_panel_init_menu_draw(self, context):
##	self.layout.operator("mmd_tools.init_scene")
#	self.layout.operator("mmd_tools.create_scene")

#def register():
#	bpy.utils.register_class(MMDToolsRenderEngine)
#	mmdtools_engine_add()
#	bpy.utils.register_class(MMDToolsInitScene)
#	bpy.utils.register_class(MMDToolsCreateScene)
#	bpy.types.OBJECT_PT_mmd_tools_object.append(mmd_tools_panel_init_menu_draw)

#def unregister():
#	bpy.types.OBJECT_PT_mmd_tools_object.remove(mmd_tools_panel_init_menu_draw)
#	bpy.utils.unregister_class(MMDToolsCreateScene)
#	bpy.utils.unregister_class(MMDToolsInitScene)
#	mmdtools_engine_remove()
#	bpy.utils.unregister_class(MMDToolsRenderEngine)

#if __name__ == "__main__":
#	register()
