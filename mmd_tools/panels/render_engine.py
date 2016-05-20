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

def register():
	bpy.utils.register_class(MMDToolsRenderEngine)

	for cp in mmdtools_compat_panels:
		if hasattr(bpy.types, cp):
			panel = getattr(bpy.types, cp)
			panel.COMPAT_ENGINES.add('mmd_tools_engine')

def unregister():
	for cp in mmdtools_compat_panels:
		if hasattr(bpy.types, cp):
			panel = getattr(bpy.types, cp)
			panel.COMPAT_ENGINES.remove('mmd_tools_engine')

	bpy.utils.unregister_class(MMDToolsRenderEngine)

if __name__ == "__main__":
	register()
