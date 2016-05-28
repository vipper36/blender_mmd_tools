# -*- coding: utf-8 -*-

import bpy

from . import root, camera, material, bone, rigid_body
from bpy.app.handlers import persistent
from mmd_tools.core.material import new_mmd_material, new_material_vg, mmd_mat_vg_update

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
        },
    bpy.types.Material: {
        'mmd_material': bpy.props.PointerProperty(type=material.MMDMaterial),
        },
    bpy.types.PoseBone: {
        'mmd_bone': bpy.props.PointerProperty(type=bone.MMDBone),
        'is_mmd_shadow_bone': bpy.props.BoolProperty(name='is_mmd_shadow_bone', default=False),
        'mmd_shadow_bone_type': bpy.props.StringProperty(name='mmd_shadow_bone_type'),
        }
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

