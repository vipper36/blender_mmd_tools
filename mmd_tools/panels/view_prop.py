# -*- coding: utf-8 -*-

from bpy.types import Panel, Operator
import bpy

import mmd_tools.core.model as mmd_model

class _PanelBase(object):
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'

class MMDModelObjectDisplayPanel(_PanelBase, Panel):
    bl_idname = 'OBJECT_PT_mmd_tools_root_object_display'
    bl_label = 'MMD Display'

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        if obj is None:
            return False

        root = mmd_model.Model.findRoot(obj)
        if root is None:
            return False

        return True

    def draw(self, context):
        layout = self.layout
        obj = context.active_object

        root = mmd_model.Model.findRoot(obj)

        row = layout.row(align=True)
        c = row.column(align=True)
        c.prop(root.mmd_root, 'show_meshes', text='Mesh')
        c.prop(root.mmd_root, 'show_armature', text='Armature')
        c.prop(root.mmd_root, 'show_rigid_bodies', text='Rigidbody')
        c.prop(root.mmd_root, 'show_joints', text='Joint')
        c = row.column(align=True)
        c.prop(root.mmd_root, 'show_temporary_objects', text='Temporary Object')
        c.prop(root.mmd_root, 'show_names_of_rigid_bodies', text='Rigidbody Name')
        c.prop(root.mmd_root, 'show_names_of_joints', text='Joint Name')

        c.prop(obj, 'is_mmd_wireframe', text='Wireframe (Shaded)')

        layout.prop(obj, 'mmd_edge_weight', text='Edge Weight')

        if context.scene.render.engine in {'BLENDER_RENDER', 'BLENDER_GAME'}:
            row = layout.row(align=True)
            row.prop(root.mmd_root, 'use_toon_texture', text='Toon Texture')
            row.prop(root.mmd_root, 'use_sphere_texture', text='Sphere Texture')

class MMDSetBackgroundToBlack(Operator):
    bl_idname = 'mmd_tools.set_background_to_black'
    bl_label = 'Set Background to Black'
    bl_description = ''
    bl_options = {'UNDO'}

    def execute(self, context):
        context.scene.world.horizon_color = [0.0, 0.0, 0.0]
        return {'FINISHED'}

class MMDSetBackgroundToWhite(Operator):
    bl_idname = 'mmd_tools.set_background_to_white'
    bl_label = 'Set Background to White'
    bl_description = ''
    bl_options = {'UNDO'}

    def execute(self, context):
        context.scene.world.horizon_color = [1.0, 1.0, 1.0]
        return {'FINISHED'}

class MMDViewPanel(_PanelBase, Panel):
    bl_idname = 'OBJECT_PT_mmd_tools_view'
    bl_label = 'MMD View'
    def draw(self, context):
        layout = self.layout
#        layout.prop(context.scene.world, 'is_mmd_ground_shadow', text='Ground Shadow')
        if context.scene.world.mmd_shadow_catcher in bpy.data.objects:
            layout.label("Ground Shadow:")
            layout.prop(bpy.data.objects[context.scene.world.mmd_shadow_catcher], 'hide_render',
                        text='Disable')
            layout.prop(context.scene.world, 'is_mmd_ground_shadow_transparent',
                        text='Transparent')
            layout.prop(context.scene.world, 'mmd_ground_shadow_compat_color',
                        text='Color')
            layout.label("Self Shadow:")
            layout.prop(context.scene.render, 'use_raytrace',
                        text='Enable')
            layout.label("Background:")
            r = layout.row(align=True)
            r.operator('mmd_tools.set_background_to_white', text='To white')
            r.operator('mmd_tools.set_background_to_black', text='To black')
            layout.label("Transparent Override:")
            r = layout.row(align=True)
            tror_mat = bpy.data.materials["mmd_tools Transparent Override"]
#            layout.prop(tror_mat, 'use_transparency', text='Enable')
            layout.prop(tror_mat, 'alpha', text='Alpha')

#class MMDViewPanel(_PanelBase, Panel):
#    bl_idname = 'OBJECT_PT_mmd_tools_view'
#    bl_label = 'MMD Shading'
#
#    def draw(self, context):
#        layout = self.layout
#
#        col = layout.column()
#        c = col.column(align=True)
#        r = c.row(align=True)
#        r.operator('mmd_tools.set_glsl_shading', text='GLSL')
#        r.operator('mmd_tools.set_shadeless_glsl_shading', text='Shadeless')
#        r = c.row(align=True)
#        r.operator('mmd_tools.reset_shading', text='Reset')

