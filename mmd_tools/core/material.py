# -*- coding: utf-8 -*-

import logging
import os

import bpy
from mmd_tools.bpyutils import addon_preferences, select_object
from mmd_tools.core.exceptions import MaterialNotFoundError

SPHERE_MODE_OFF    = 0
SPHERE_MODE_MULT   = 1
SPHERE_MODE_ADD    = 2
SPHERE_MODE_SUBTEX = 3

class FnMaterial(object):
    __BASE_TEX_SLOT = 0
    __TOON_TEX_SLOT = 1
    __SPHERE_TEX_SLOT = 2

    def __init__(self, material=None):
        self.__material = material

    @classmethod
    def from_material_id(cls, material_id):
        for material in bpy.data.materials:
            if material.mmd_material.material_id == material_id:
                return cls(material)
        return None

    @classmethod
    def swap_materials(cls, meshObj, mat1_ref, mat2_ref, reverse=False,
                       swap_slots=False):
        """
        This method will assign the polygons of mat1 to mat2.
        If reverse is True it will also swap the polygons assigned to mat2 to mat1.
        The reference to materials can be indexes or names
        Finally it will also swap the material slots if the option is given.
        """
        try:
            # Try to find the materials
            mat1 = meshObj.data.materials[mat1_ref]
            mat2 = meshObj.data.materials[mat2_ref]
            if None in (mat1, mat2):
                raise MaterialNotFoundError()
        except (KeyError, IndexError):
            # Wrap exceptions within our custom ones
            raise MaterialNotFoundError()
        mat1_idx = meshObj.data.materials.find(mat1.name)
        mat2_idx = meshObj.data.materials.find(mat2.name)
        with select_object(meshObj):
            # Swap polygons
            for poly in meshObj.data.polygons:
                if poly.material_index == mat1_idx:
                    poly.material_index = mat2_idx
                elif reverse and poly.material_index == mat2_idx:
                    poly.material_index = mat1_idx
            # Swap slots if specified
            if swap_slots:
                meshObj.material_slots[mat1_idx].material = mat2
                meshObj.material_slots[mat2_idx].material = mat1
        return mat1, mat2

    @classmethod
    def fixMaterialOrder(cls, meshObj, material_names):
        """
        This method will fix the material order. Which is lost after joining meshes.
        """
        for new_idx, mat in enumerate(material_names):
            # Get the material that is currently on this index
            other_mat = meshObj.data.materials[new_idx]
            if other_mat.name == mat:
                continue  # This is already in place
            cls.swap_materials(meshObj, mat, new_idx, reverse=True, swap_slots=True)

    @property
    def material_id(self):
        mmd_mat = self.__material.mmd_material
        if mmd_mat.material_id < 0:
            max_id = -1
            for mat in bpy.data.materials:
                max_id = max(max_id, mat.mmd_material.material_id)
            mmd_mat.material_id = max_id + 1
        return mmd_mat.material_id

    @property
    def material(self):
        return self.__material


    def __same_image_file(self, image, filepath):
        if image and image.source == 'FILE':
            img_filepath = image.filepath_from_user()
            if img_filepath == filepath:
                return True
            try:
                return os.path.samefile(img_filepath, filepath)
            except:
                pass
        return False

    def __load_image(self, filepath):
        for i in bpy.data.images:
            if self.__same_image_file(i, filepath):
                return i

        try:
            return bpy.data.images.load(filepath)
        except:
            logging.warning('Cannot create a texture for %s. No such file.', filepath)

        img = bpy.data.images.new(os.path.basename(filepath), 1, 1)
        img.source = 'FILE'
        img.filepath = filepath
        return img

    def __load_texture(self, filepath):
        for t in bpy.data.textures:
            if t.type == 'IMAGE' and self.__same_image_file(t.image, filepath):
                return t
        tex = bpy.data.textures.new(name=bpy.path.display_name_from_filepath(filepath), type='IMAGE')
        tex.image = self.__load_image(filepath)
        return tex


    def get_texture(self):
        return self.__get_texture(self.__BASE_TEX_SLOT)

    def __get_texture(self, index):
        texture_slot = self.__material.texture_slots[index]
        return texture_slot.texture if texture_slot else None

    def __use_texture(self, index, use_tex):
        texture_slot = self.__material.texture_slots[index]
        if texture_slot:
            texture_slot.use = use_tex

    def create_texture(self, filepath):
        """ create a texture slot for textures of MMD models.

        Args:
            material: the material object to add a texture_slot
            filepath: the file path to texture.

        Returns:
            bpy.types.MaterialTextureSlot object
        """
        mat = self.__material
        mmd_mat = self.__material.mmd_material
        texture_slot = self.__material.texture_slots.create(self.__BASE_TEX_SLOT)
        texture_slot.use_map_alpha = True
        texture_slot.texture_coords = 'UV'
        texture_slot.blend_type = 'MULTIPLY'
        texture_slot.texture = self.__load_texture(filepath)
        mat.node_tree.nodes["Tex"].texture = texture_slot.texture
        mat.node_tree.nodes["Alpha Mul"].material.texture_slots[0].texture = texture_slot.texture
        mat.node_tree.nodes["Use Tex"].inputs[0].default_value = 1.0
        return texture_slot

    def remove_texture(self):
        mat = self.__material
        mat.node_tree.nodes["Tex"].texture = None
        mat.node_tree.nodes["Alpha Mul"].material.texture_slots[0].texture = None
        mat.node_tree.nodes["Use Tex"].inputs[0].default_value = 0.0
        self.__remove_texture(self.__BASE_TEX_SLOT)

    def __remove_texture(self, index):
        texture_slot = self.__material.texture_slots[index]
        if texture_slot:
            tex = texture_slot.texture
            self.__material.texture_slots.clear(index)
            #print('clear texture: %s  users: %d'%(tex.name, tex.users))
            if tex and tex.users < 1 and tex.type == 'IMAGE':
                #print(' - remove texture: '+tex.name)
                img = tex.image
                tex.image = None
                bpy.data.textures.remove(tex)
                if img and img.users < 1:
                    #print('    - remove image: '+img.name)
                    bpy.data.images.remove(img)


    def get_sphere_texture(self):
        return self.__get_texture(self.__SPHERE_TEX_SLOT)

    def use_sphere_texture(self, use_sphere):
        if use_sphere:
            self.update_sphere_texture_type()
        else:
            self.__use_texture(self.__SPHERE_TEX_SLOT, use_sphere)

    def create_sphere_texture(self, filepath):
        """ create a texture slot for environment mapping textures of MMD models.

        Args:
            material: the material object to add a texture_slot
            filepath: the file path to environment mapping texture.

        Returns:
            bpy.types.MaterialTextureSlot object
        """
        mat = self.__material
        mmd_mat = self.__material.mmd_material

        texture_slot = self.__material.texture_slots.create(self.__SPHERE_TEX_SLOT)
        texture_slot.texture_coords = 'NORMAL'
        texture_slot.texture = self.__load_texture(filepath)
        texture_slot.texture.use_alpha = texture_slot.texture.image.use_alpha = False
        mat.node_tree.nodes["Sphere Tex"].texture = texture_slot.texture
        self.update_sphere_texture_type()
        return texture_slot

    def update_sphere_texture_type(self):
        mat = self.__material
        mmd_mat = self.__material.mmd_material

        texture_slot = self.__material.texture_slots[self.__SPHERE_TEX_SLOT]
        if not texture_slot:
            return
        sphere_texture_type = int(self.__material.mmd_material.sphere_texture_type)
        if sphere_texture_type not in (1, 2, 3):
            texture_slot.use = False
            mat.node_tree.nodes["Use Sphere Tex"].inputs[0].default_value = 0.0
        else:
            texture_slot.use = True
            mat.node_tree.nodes["Mix Tex"].blend_type = ('MULTIPLY', 'ADD', 'MULTIPLY')[sphere_texture_type-1]
            mat.node_tree.nodes["Use Sphere Tex"].inputs[0].default_value = 1.0
            if sphere_texture_type == 2:
                mat.node_tree.nodes["Use Sphere Tex"].inputs[1].default_value = [0.0, 0.0, 0.0, 1.0]
            else:
                mat.node_tree.nodes["Use Sphere Tex"].inputs[1].default_value = [1.0, 1.0, 1.0, 1.0]
            if sphere_texture_type == 3:
                mat.node_tree.links.new(mat.node_tree.nodes["Sphere Tex"].inputs[0], mat.node_tree.nodes["Geo2"].outputs[4]) # Additional UV
            else:
                mat.node_tree.links.new(mat.node_tree.nodes["Sphere Tex"].inputs[0], mat.node_tree.nodes["Geo"].outputs[5])

            texture_slot.blend_type = ('MULTIPLY', 'ADD', 'MULTIPLY')[sphere_texture_type-1] # for debug?

    def remove_sphere_texture(self):
        mat = self.__material
        mmd_mat = self.__material.mmd_material
        self.__remove_texture(self.__SPHERE_TEX_SLOT)
        mat.node_tree.nodes["Sphere Tex"].texture = None
        mat.node_tree.nodes["Use Sphere Tex"].inputs[0].default_value = 0.0

    def get_toon_texture(self):
        return self.__get_texture(self.__TOON_TEX_SLOT)

    def use_toon_texture(self, use_toon):
        self.__use_texture(self.__TOON_TEX_SLOT, use_toon)

    def create_toon_texture(self, filepath):
        """ create a texture slot for toon textures of MMD models.

        Args:
            material: the material object to add a texture_slot
            filepath: the file path to toon texture.

        Returns:
            bpy.types.MaterialTextureSlot object
        """
        texture_slot = self.__material.texture_slots.create(self.__TOON_TEX_SLOT)
        texture_slot.texture_coords = 'NORMAL'
        texture_slot.blend_type = 'MULTIPLY'
        texture_slot.texture = self.__load_texture(filepath)
        texture_slot.texture.use_alpha = texture_slot.texture.image.use_alpha = False
        texture_slot.texture.extension = 'EXTEND'
        return texture_slot

    def update_toon_texture(self):
        mat = self.__material
        mmd_mat = self.__material.mmd_material
        if mmd_mat.is_shared_toon_texture:
            #shared_toon_folder = addon_preferences('shared_toon_folder', '')
            #toon_path = os.path.join(shared_toon_folder, 'toon%02d.bmp'%(mmd_mat.shared_toon_texture+1))
            #self.create_toon_texture(bpy.path.resolve_ncase(path=toon_path))
            mat.node_tree.nodes["mmd_tools_shader"].inputs[7].default_value = mmd_mat.shared_toon_texture
        elif mmd_mat.toon_texture != '':
            slot = self.create_toon_texture(mmd_mat.toon_texture)
            mat.node_tree.nodes["mmd_tools_shader"].inputs[7].default_value = -1.0
            mat.node_tree.nodes["mmd_tools_shader"].inputs[9].default_value = 1.0
            mat.node_tree.nodes["Toon Tex"].texture = slot.texture
        else:
            self.remove_toon_texture()
            mat.node_tree.nodes["mmd_tools_shader"].inputs[7].default_value = -1.0
            mat.node_tree.nodes["mmd_tools_shader"].inputs[9].default_value = 0.0

    def remove_toon_texture(self):
        self.__remove_texture(self.__TOON_TEX_SLOT)

    def update_ambient_color(self):
        mat = self.__material
        mmd_mat = mat.mmd_material
        mat.node_tree.nodes["mmd_tools_shader"].inputs[4].default_value = list(mmd_mat.ambient_color) + [1.0]

    def update_diffuse_color(self):
        mat = self.__material
        mmd_mat = mat.mmd_material
        mat.node_tree.nodes["mmd_tools_shader"].inputs[0].default_value = list(mmd_mat.diffuse_color) + [1.0]

    def update_alpha(self):
        mat = self.__material
        mmd_mat = mat.mmd_material
#        mat.alpha = mmd_mat.alpha
        mat.node_tree.nodes["Alpha Mul"].material.alpha = mmd_mat.alpha

    def update_specular_color(self):
        mat = self.__material
        mmd_mat = mat.mmd_material
        mat.node_tree.nodes["mmd_tools_shader"].inputs[2].default_value = list(mmd_mat.specular_color) + [1.0]

    def update_shininess(self):
        mat = self.__material
        mmd_mat = mat.mmd_material
        shininess = mmd_mat.shininess
        spw_mat = mat.node_tree.nodes["Spec Weight"].material
        spw_mat.specular_hardness = shininess
        mat.node_tree.nodes["mmd_tools_shader"].inputs[1].default_value = shininess
        if shininess > 0:
            spw_mat.specular_intensity = 1.0
        else:
            spw_mat.specular_intensity = 0

    def update_is_double_sided(self):
        mat = self.__material
        mmd_mat = mat.mmd_material
        mat.node_tree.nodes["Is Single"].inputs[1].default_value = float(mmd_mat.is_double_sided)
#        mat.game_settings.use_backface_culling = not mmd_mat.is_double_sided

    def update_drop_shadow(self):
        mat = self.__material
        mmd_mat = mat.mmd_material
        mat.use_cast_shadows = mmd_mat.enabled_self_shadow_map or mmd_mat.enabled_drop_shadow
        mat.use_cast_buffer_shadows = mmd_mat.enabled_drop_shadow

    def update_self_shadow_map(self):
        mat = self.__material
        mmd_mat = mat.mmd_material
        mat.use_cast_shadows = mmd_mat.enabled_self_shadow_map or mmd_mat.enabled_drop_shadow
        mat.use_raytrace = mmd_mat.enabled_self_shadow_map

    def update_self_shadow(self):
        mat = self.__material
        mmd_mat = mat.mmd_material
        if mmd_mat.enabled_self_shadow:
            mat.node_tree.nodes["Pure Mat"].material = bpy.data.materials["mmd_tools Node Base"]
        else:
            mat.node_tree.nodes["Pure Mat"].material = bpy.data.materials["mmd_tools Node Base NoShadow"]

#        mat.use_shadows = mmd_mat.enabled_self_shadow
#        mat.use_transparent_shadows = mmd_mat.enabled_self_shadow

    def update_enabled_toon_edge(self):
        mat = self.__material
        mmd_mat = mat.mmd_material
        edge_mat = bpy.data.materials[mmd_mat.edge_mat_name]
#        if not hasattr(mat, 'line_color'): # freestyle line color
#            return
        mmd_mat = mat.mmd_material
        edge_mat.node_tree.nodes["Edge Alpha"].inputs[0].default_value = float(mmd_mat.enabled_toon_edge) * mmd_mat.edge_color[3]

#        mat.line_color[3] = min(int(mmd_mat.enabled_toon_edge), mmd_mat.edge_color[3])

    def update_edge_color(self):
        mat = self.__material
        mmd_mat = mat.mmd_material
        edge_mat = bpy.data.materials[mmd_mat.edge_mat_name]
#        if not hasattr(mat, 'line_color'): # freestyle line color
#            return
        mmd_mat = mat.mmd_material
        edge_mat.node_tree.nodes["Edge Base"].inputs[0].default_value = list(mmd_mat.edge_color)[0:3] + [1.0]
        edge_mat.node_tree.nodes["Edge Alpha"].inputs[0].default_value =float(mmd_mat.enabled_toon_edge) * mmd_mat.edge_color[3]
#        r, g, b, a = mmd_mat.edge_color
#        mat.line_color = [r, g, b, min(int(mmd_mat.enabled_toon_edge), a)]

    def update_edge_weight(self):
#        pass
        mat = self.__material
        mmd_mat = mat.mmd_material
        for i in mmd_mat.vgs:
            bpy.data.objects[i.obj_name].modifiers[i.vg_name].mask_constant = mmd_mat.edge_weight/100.0

def new_mmd_material():
    pass

