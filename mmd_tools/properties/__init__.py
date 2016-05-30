# -*- coding: utf-8 -*-

import bpy

from . import root, camera, material, bone, rigid_body
from bpy.app.handlers import persistent
from mmd_tools.core.material import new_mmd_material, new_material_vg, mmd_mat_vg_update

#def _updateGroundShadow(prop, context):
#    wo = prop.id_data
#    if wo.mmd_shadow_catcher in bpy.data.objects:
#        bpy.data.objects[wo.mmd_shadow_catcher].hide_render = not wo.is_mmd_ground_shadow

def _updateGroundShadowTransparent(prop, context):
    wo = prop.id_data
    if wo.mmd_shadow_catcher in bpy.data.objects:
        nodes = bpy.data.objects[wo.mmd_shadow_catcher].active_material.node_tree.nodes
        # XXX: MMD uses (color / 256 * 255)?
        if wo.is_mmd_ground_shadow_transparent:
            nodes["Alpha to New Alpha"].inputs[1].default_value = 0.65
            nodes["Color"].inputs[1].default_value = [wo.mmd_ground_shadow_compat_color]*3 + [1]
        else:
            nodes["Alpha to New Alpha"].inputs[1].default_value = 1.0
            nodes["Color"].inputs[1].default_value = [wo.mmd_ground_shadow_compat_color]*3 + [1]

def _updateGroundShadowCompatColor(prop, context):
    _updateGroundShadowTransparent(prop, context)

def _updateWireframe(prop, context):
    ob = prop.id_data
    ob.modifiers["Shaded Wireframe"].show_viewport = ob.is_mmd_wireframe
    ob.modifiers["Shaded Wireframe"].show_render = ob.is_mmd_wireframe
    ob.modifiers["Edge Solidify"].show_viewport = not ob.is_mmd_wireframe
    ob.modifiers["Edge Solidify"].show_render = not ob.is_mmd_wireframe

__properties = {
    bpy.types.Object: {
        'mmd_type': bpy.props.EnumProperty(
            name='Type',
            default='NONE',
            items=[
                ('NONE', 'None', '', 1),
                ('ROOT', 'Root', '', 2),
                ('RIGID_GRP_OBJ', 'Rigid Body Grp Empty', '', 3),
                ('JOINT_GRP_OBJ', 'Joint Grp Empty', '', 4),
                ('TEMPORARY_GRP_OBJ', 'Temporary Grp Empty', '', 5),

                ('CAMERA', 'Camera', '', 21),
                ('JOINT', 'Joint', '', 22),
                ('RIGID_BODY', 'Rigid body', '', 23),
                ('LIGHT', 'Light', '', 24),

                ('TRACK_TARGET', 'Track Target', '', 51),
                ('NON_COLLISION_CONSTRAINT', 'Non Collision Constraint', '', 52),
                ('SPRING_CONSTRAINT', 'Spring Constraint', '', 53),
                ('SPRING_GOAL', 'Spring Goal', '', 54),
                ]
            ),
        'mmd_root': bpy.props.PointerProperty(type=root.MMDRoot),
        'mmd_camera': bpy.props.PointerProperty(type=camera.MMDCamera),
        'mmd_rigid': bpy.props.PointerProperty(type=rigid_body.MMDRigidBody),
        'mmd_joint': bpy.props.PointerProperty(type=rigid_body.MMDJoint),
        'is_mmd_lamp': bpy.props.BoolProperty(name='is_mmd_lamp', default=False),
        'is_mmd_glsl_light': bpy.props.BoolProperty(name='is_mmd_glsl_light', default=False),
        'is_mmd_wireframe': bpy.props.BoolProperty(name='is_mmd_wireframe', default=False, update=_updateWireframe),
        },
    bpy.types.Material: {
        'mmd_material': bpy.props.PointerProperty(type=material.MMDMaterial),
        },
    bpy.types.PoseBone: {
        'mmd_bone': bpy.props.PointerProperty(type=bone.MMDBone),
        'is_mmd_shadow_bone': bpy.props.BoolProperty(name='is_mmd_shadow_bone', default=False),
        'mmd_shadow_bone_type': bpy.props.StringProperty(name='mmd_shadow_bone_type'),
        },
    bpy.types.World: {
        'mmd_shadow_catcher': bpy.props.StringProperty(name='shadow_catcher'),
#        'is_mmd_ground_shadow': bpy.props.BoolProperty(name='is_mmd_ground_shadow', default=True, update=_updateGroundShadow),
        'is_mmd_ground_shadow_transparent': bpy.props.BoolProperty(name='is_mmd_ground_shadow_transparent', default=True, update=_updateGroundShadowTransparent),
        'mmd_ground_shadow_compat_color': bpy.props.FloatProperty(name='mmd_ground_shadow_compat_color', default=1.0, min=0, max=2.0, step=0.1, update=_updateGroundShadowCompatColor),
        },
    }


@persistent
def mmd_material_scene_update(scene):
    if hasattr(bpy.context, "object") and bpy.context.object and bpy.context.object.active_material and \
       bpy.context.object.active_material.is_updated and \
       bpy.context.scene.render.engine == 'MMD_TOOLS_ENGINE':
        ob = bpy.context.object
        mat = ob.active_material

        if mat and (mat.name.find(".edge")>=0 or mat.name.find(".alp")>=0 or mat.name.find(".spw")>=0):
            mat = ob.active_material = None

# weight update (should consider assigned None material)
# also handle weight groups adding/removing
        if not mat or mat.mmd_material.edge_mat_name != "":
            mmd_mat_vg_update(ob)

#        if len(ob.material_slots) == 0:
#            bpy.ops.object.material_slot_add() # XXX: cause recursive loop

        if bpy.context.object.active_material_index+1 >= len(ob.material_slots):
             return
#            bpy.ops.object.material_slot_add() # XXX: cause recursive loop
#            bpy.context.object.active_material_index -= 1

        if not mat:
            edge_mat = None
        elif mat.mmd_material.edge_mat_name == "":
            edge_mat, mat_vtx = new_mmd_material(mat.name, mat, ob)
        else:
            edge_mat = bpy.data.materials[mat.mmd_material.edge_mat_name]

        ob.material_slots[bpy.context.object.active_material_index+1].material = edge_mat

def register():
    for typ, t in __properties.items():
        for attr, prop in t.items():
            setattr(typ, attr, prop)

    bpy.app.handlers.scene_update_pre.append(mmd_material_scene_update)

def unregister():
    for typ, t in __properties.items():
        for attr in t.keys():
            delattr(typ, attr)

