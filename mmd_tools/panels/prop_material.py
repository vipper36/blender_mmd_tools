# -*- coding: utf-8 -*-

from bpy.types import Panel, UIList, UI_UL_list

from mmd_tools.core.material import FnMaterial, new_mmd_material
import bpy

# https://www.blender.org/api/blender_python_api_2_77_release/bpy.types.UIList.html
class MMDMaterialSlot(UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        mat = item.material
        if mat and mat.name.find(".edge")>=0:
            col = layout.column()
            col.enabled = False
            col.alignment = 'LEFT'
            col.prop(mat, "name", text="", emboss=False, icon_value=icon)
        elif mat:
            layout.prop(mat, "name", text="", emboss=False, icon_value=icon)
        else:
            layout.label(text="", icon_value=icon)

    def filter_items(self, context, data, propname):
        mats = getattr(data, propname)
        helper_funcs = UI_UL_list

        flt_flags = []

        if self.filter_name:
            flt_flags = helper_funcs.filter_items_by_name(self.filter_name, self.bitflag_filter_item, mats, "name")

        if not flt_flags:
            flt_flags = [self.bitflag_filter_item] * len(mats)

        edge_space = False
        for idx, mat in enumerate(mats):
            if not mat.material and not edge_space:
                edge_space=True
                continue
            if mat.material and not mat.material.name.find(".edge")>=0:
                edge_space=True
                continue

            if ((not mat.material) or mat.material.name.find(".edge")>=0) and not self.use_filter_invert:
                flt_flags[idx] &= ~self.bitflag_filter_item
            elif ((not mat.material) or mat.material.name.find(".edge")>=0) and self.use_filter_invert:
                flt_flags[idx] |= self.bitflag_filter_item

            edge_space=False

        flt_neworder = []
        if self.use_filter_sort_alpha:
            flt_neworder = helper_funcs.sort_items_by_name(mats, "name")

        return flt_flags, flt_neworder


class MMDMaterialSlotAdd(bpy.types.Operator):
    """Add New Material Slot"""
    bl_idname = "mmd_tools.material_slot_add"
    bl_label = "Add Material Slot"
    bl_options = {'REGISTER'}

    def execute(self, context):
        ob = context.object
        if len(ob.material_slots) > 0 and ob.material_slots[-1].material and \
           not ob.material_slots[-1].material.name.find(".edge")>=0:
            bpy.ops.object.material_slot_add() # add last material edge

        bpy.ops.object.material_slot_add()
        idx = bpy.context.object.active_material_index
        bpy.ops.object.material_slot_add()
        bpy.context.object.active_material_index = idx
        return {'FINISHED'}

class MMDMaterialSlotRemove(bpy.types.Operator):
    """Remove Material Slot"""
    bl_idname = "mmd_tools.material_slot_remove"
    bl_label = "Remove Material Slot"
    bl_options = {'REGISTER'}

    def execute(self, context):
        slot = context.material_slot
        ob = context.object

        if len(ob.material_slots) == 0:
            return {'CANCELLED'}

        edge_mat_name = None

        if slot.material:
            edge_mat_name = slot.material.mmd_material.edge_mat_name

        bpy.ops.object.material_slot_remove()

        if len(ob.material_slots) == 0:
            return {'FINISHED'}

        idx = bpy.context.object.active_material_index

        if (not ob.material_slots[idx].material) or \
           ob.material_slots[idx].material.name == edge_mat_name:
            bpy.ops.object.material_slot_remove()

        if bpy.context.object.active_material_index > 1 and \
           bpy.context.object.active_material_index >= len(ob.material_slots)-1: # if edge space
            bpy.context.object.active_material_index -= 1
        return {'FINISHED'}


class MMDMaterialSlotMoveUp(bpy.types.Operator):
    """Move Material Slot"""
    bl_idname = "mmd_tools.material_slot_move_up"
    bl_label = "Move Material Slot"
    bl_options = {'REGISTER'}

    def execute(self, context):
        slot = context.material_slot
        ob = context.object

        bpy.ops.object.material_slot_move(direction='UP')
        bpy.ops.object.material_slot_move(direction='UP')
        bpy.context.object.active_material_index += 3
        bpy.ops.object.material_slot_move(direction='UP')
        bpy.ops.object.material_slot_move(direction='UP')
        bpy.context.object.active_material_index -= 1

        return {'FINISHED'}


class MMDMaterialSlotMoveDown(bpy.types.Operator):
    """Move Material Slot"""
    bl_idname = "mmd_tools.material_slot_move_down"
    bl_label = "Move Material Slot"
    bl_options = {'REGISTER'}

    def execute(self, context):
        slot = context.material_slot
        ob = context.object

        bpy.ops.object.material_slot_move(direction='DOWN')
        bpy.ops.object.material_slot_move(direction='DOWN')
        bpy.ops.object.material_slot_move(direction='DOWN')
        bpy.context.object.active_material_index -= 3
        bpy.ops.object.material_slot_move(direction='DOWN')
        bpy.ops.object.material_slot_move(direction='DOWN')
        bpy.ops.object.material_slot_move(direction='DOWN')
        bpy.context.object.active_material_index -= 1

        return {'FINISHED'}

class MMDMaterialSlotAssign(bpy.types.Operator):
    """Assign Material Slot"""
    bl_idname = "mmd_tools.material_slot_assign"
    bl_label = "Assign Material Slot"
    bl_options = {'REGISTER'}

    def execute(self, context):
        slot = context.material_slot
        ob = context.object
        if bpy.context.object.active_material_index+1 >= len(ob.material_slots):
            bpy.ops.object.material_slot_add()
        if slot.material.mmd_material.edge_mat_name == "":
            edge_mat, mat_vtx = new_mmd_material(slot.material.name, slot.material, ob)
        ob.material_slots[bpy.context.object.active_material_index+1].material = \
          bpy.data.materials[slot.material.mmd_material.edge_mat_name]

        # TODO: update material vertex weight

        bpy.ops.object.material_slot_assign()
        return {'FINISHED'}

class MMDMaterialNew(bpy.types.Operator):
    """Create New Material"""
    bl_idname = "mmd_tools.material_new"
    bl_label = "Create New Material"
    bl_options = {'REGISTER'}

    def execute(self, context):
        slot = context.material_slot
        ob = context.object
        bpy.ops.material.new()

# already handled by mmd_material_scene_update
#        if bpy.context.object.active_material_index+1 < len(ob.material_slots):
#            old_edge_mat = ob.material_slots[bpy.context.object.active_material_index+1].material
#            new_edge_mat = None
#            if old_edge_mat:
#                new_edge_mat = bpy.data.materials.new(old_edge_mat.name)
#                new_edge_mat= old_edge_mat.copy()
#                slot.material.mmd_material.edge_mat_name = new_edge_mat.name
#            else:
#                new_edge_mat, mat_vtx = new_mmd_material(slot.material.name, slot.material, ob)
#
#            ob.material_slots[bpy.context.object.active_material_index+1].material = new_edge_mat

        return {'FINISHED'}


class MMDMaterialUnlink(bpy.types.Operator):
    """Create Unlink Material"""
    bl_idname = "mmd_tools.material_unlink"
    bl_label = "Unlink Material"
    bl_options = {'REGISTER'}

    def execute(self, context):
        ob = context.object
        ob.material_slots[bpy.context.object.active_material_index].material = None
        if bpy.context.object.active_material_index+1 < len(ob.material_slots):
            ob.material_slots[bpy.context.object.active_material_index+1].material = None
        return {'FINISHED'}

class MMDMaterialSlotPanel(Panel):
    bl_label = ""
    bl_options = {'HIDE_HEADER'}
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "material"

    @classmethod
    def poll(cls, context):
        return (context.material or context.object) and \
                 context.scene.render.engine == 'mmd_tools_engine'

    def draw(self, context):
        layout = self.layout

        slot = context.material_slot
        ob = context.object
        mat = context.material
        space = context.space_data

        is_sortable = -1
        if ob:
            edge_space = False
            for s in ob.material_slots:
                if not s.material and not edge_space:
                    is_sortable += 1
                    edge_space=True
                    continue
                if s.material and not s.material.name.find(".edge")>=0:
                    is_sortable += 1
                    edge_space=True
                    continue
                edge_space=False
                if is_sortable == 1:
                    break

        if is_sortable == -1:
            is_sortable = 0

        if ob:
            row = layout.row()

            row.template_list("MMDMaterialSlot", "", ob, "material_slots", ob, "active_material_index")

            col = row.column(align=True)
            col.operator("mmd_tools.material_slot_add", icon='ZOOMIN', text="")
            col.operator("mmd_tools.material_slot_remove", icon='ZOOMOUT', text="")

            # col.menu("MATERIAL_MT_specials", icon='DOWNARROW_HLT', text="")

            if is_sortable:
                col.separator()

                col.operator("mmd_tools.material_slot_move_up", icon='TRIA_UP', text="")
                col.operator("mmd_tools.material_slot_move_down", icon='TRIA_DOWN', text="")

            if ob.mode == 'EDIT':
                row = layout.row(align=True)
                row.operator("mmd_tools.material_slot_assign", text="Assign")
                row.operator("object.material_slot_select", text="Select")
                row.operator("object.material_slot_deselect", text="Deselect")

        split = layout.split(percentage=0.65)

        if ob:
            # "update" is handling in mmd_material_scene_update
            split.template_ID(ob, "active_material", new="mmd_tools.material_new", unlink="mmd_tools.material_unlink")
            row = split.row()

            if slot:
                row.prop(slot, "link", text="")
            else:
                row.label()
        elif mat:
            split.template_ID(space, "pin_id")
            split.separator()

class MMDMaterialPanel(Panel):
    bl_idname = 'MATERIAL_PT_mmd_tools_material'
    bl_label = 'MMD Material'
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = 'material'

    @classmethod
    def poll(cls, context):
        material = context.active_object.active_material
        return material and material.mmd_material and not material.name.find(".edge")>=0

    def draw(self, context):
        material = context.active_object.active_material
        mmd_material = material.mmd_material

        layout = self.layout

        col = layout.column(align=True)
        col.label('Information:')
        c = col.column()
        r = c.row()
        r.prop(mmd_material, 'name_j')
        r = c.row()
        r.prop(mmd_material, 'name_e')
        r = c.row()
        r.prop(mmd_material, 'comment')

        col = layout.column(align=True)
        col.label('Color:')
        c = col.column()
        r = c.row()
        r.prop(mmd_material, 'diffuse_color')
        r.prop(mmd_material, 'alpha', slider=True)
        r = c.row()
        r.prop(mmd_material, 'specular_color')
        r.prop(mmd_material, 'shininess', slider=True)
        r = c.row()
        r.prop(mmd_material, 'ambient_color')
        r.label() # for alignment only

        col = layout.column(align=True)
        col.label('Shadow:')
        c = col.column()
        r = c.row()
        r.prop(mmd_material, 'is_double_sided')
        r.prop(mmd_material, 'enabled_drop_shadow')
        r = c.row()
        r.prop(mmd_material, 'enabled_self_shadow_map')
        r.prop(mmd_material, 'enabled_self_shadow')

        col = layout.column(align=True)
        col.label('Edge:')
        c = col.column()
        r = c.row()
        r.prop(mmd_material, 'enabled_toon_edge')
        r = c.row()
        r.active = mmd_material.enabled_toon_edge
        r.prop(mmd_material, 'edge_color')
        r.prop(mmd_material, 'edge_weight', slider=True)


class MMDTexturePanel(Panel):
    bl_idname = 'MATERIAL_PT_mmd_tools_texture'
    bl_label = 'MMD Texture'
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = 'material'

    @classmethod
    def poll(cls, context):
        material = context.active_object.active_material
        return material and material.mmd_material and not material.name.find(".edge")>=0

    def draw(self, context):
        material = context.active_object.active_material
        mmd_material = material.mmd_material

        layout = self.layout

        fnMat = FnMaterial(material)

        col = layout.column(align=True)
        row = col.row(align=True)
        row.label('Texture:')
        r = row.column(align=True)
        tex = fnMat.get_texture()
        if tex:
            if tex.type == 'IMAGE' and tex.image:
                r2 = r.row(align=True)
                r2.prop(tex.image, 'filepath', text='')
                r2.operator('mmd_tools.material_remove_texture', text='', icon='PANEL_CLOSE')
            else:
                r.operator('mmd_tools.material_remove_texture', text='Remove', icon='PANEL_CLOSE')
                col.label('Texture is invalid.', icon='ERROR')
        else:
            r.operator('mmd_tools.material_open_texture', text='Add', icon='FILESEL')

        col = layout.column(align=True)
        row = col.row(align=True)
        row.label('Sphere Texture:')
        r = row.column(align=True)
        tex = fnMat.get_sphere_texture()
        if tex:
            if tex.type == 'IMAGE' and tex.image:
                r2 = r.row(align=True)
                r2.prop(tex.image, 'filepath', text='')
                r2.operator('mmd_tools.material_remove_sphere_texture', text='', icon='PANEL_CLOSE')
            else:
                r.operator('mmd_tools.material_remove_sphere_texture', text='Remove', icon='PANEL_CLOSE')
                col.label('Sphere Texture is invalid.', icon='ERROR')
        else:
            r.operator('mmd_tools.material_open_sphere_texture', text='Add', icon='FILESEL')
        r = col.row(align=True)
        r.prop(mmd_material, 'sphere_texture_type')

        col = layout.column(align=True)
        c = col.column()
        r = c.row()
        r.prop(mmd_material, 'is_shared_toon_texture')
        if mmd_material.is_shared_toon_texture:
            r.prop(mmd_material, 'shared_toon_texture')
        else:
            r = c.row()
            r.prop(mmd_material, 'toon_texture')

