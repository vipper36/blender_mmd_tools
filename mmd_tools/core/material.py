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
            bpy.data.objects[i.obj_name].modifiers[i.vgm_name].mask_constant = mmd_mat.edge_weight/100.0

def mmd_shader_get():
    groups = bpy.data.node_groups
    if "mmd_tools_shader" in groups:
        return groups["mmd_tools_shader"]
    mat = bpy.data.materials.new(name="mmd_tools Node Base")

    mat_ns = bpy.data.materials.new(name="mmd_tools Node Base NoShadow")
    mat_ns.use_shadows = False
    mat_ns.use_transparent_shadows = False

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
            ["mmd_tools Lamp Data", 3],
            ["mmd_tools Group Input", 0],
        ],
        {"blend_type": "MULTIPLY", "use_clamp": True}, "mmd_tools Dif Mul"],

        ["ShaderNodeMath",[
            0.001,
            ["mmd_tools Group Input", 1], # shininess
        ], {"operation": "POWER"} , "mmd_tools LSpec Weight Base"],

        ["ShaderNodeMixRGB",[
            1.0,
            ["mmd_tools LSpec Weight Base", 0],
            ["mmd_tools Lamp Data", 3],
        ], {"blend_type": "MULTIPLY"} , "mmd_tools LSpec Weight"],

        ["ShaderNodeSeparateRGB", [["mmd_tools Group Input", 2]], None, "mmd_tools Placeholder 1"],

        ["ShaderNodeMixRGB",[
            1.0,
            ["mmd_tools Group Input", 3],
            ["mmd_tools LSpec Weight", 0],
        ], {"blend_type": "LIGHTEN"} , "mmd_tools Spec Weight"],

        ["ShaderNodeMixRGB",[
            1.0,
            ["mmd_tools Group Input", 2],
            ["mmd_tools Spec Weight", 0],
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
            ["mmd_tools Group Input", 4],
        ],
        {"blend_type": "ADD", "use_clamp": True}, "mmd_tools Amb Add"],

        ["ShaderNodeMixRGB",[
            1.0,
            ["mmd_tools Amb Add", 0],
            ["mmd_tools Group Input", 5],
        ],
        {"blend_type": "MULTIPLY", "use_clamp": True}, "mmd_tools Tex Mul"],

# TOON
        ["ShaderNodeMixRGB",[
            1.0,
            ["mmd_tools Group Input", 6],
            ["mmd_tools Lamp Data", 3],
        ],
        {"blend_type": "DIVIDE", "use_clamp": True}, "mmd_tools NL"],

        ["ShaderNodeMath",[
            1.0,
            ["mmd_tools NL", 0],
        ],
        {"operation": "SUBTRACT", "use_clamp": True}, "mmd_tools 1-NL"],

        ["ShaderNodeMath",[
            0.5,
            ["mmd_tools 1-NL", 0],
        ],
        {"operation": "MULTIPLY", "use_clamp": True}, "mmd_tools 0.5*(1-NL)"],

        ["ShaderNodeValToRGB",[["mmd_tools 0.5*(1-NL)", 0]], None, "mmd_tools ToonRamp 1"],
        ["ShaderNodeValToRGB",[["mmd_tools 0.5*(1-NL)", 0]], None, "mmd_tools ToonRamp 2"],
        ["ShaderNodeValToRGB",[["mmd_tools 0.5*(1-NL)", 0]], None, "mmd_tools ToonRamp 3"],
        ["ShaderNodeValToRGB",[["mmd_tools 0.5*(1-NL)", 0]], None, "mmd_tools ToonRamp 4"],
        ["ShaderNodeValToRGB",[["mmd_tools 0.5*(1-NL)", 0]], None, "mmd_tools ToonRamp 5"],
        ["ShaderNodeValToRGB",[["mmd_tools 0.5*(1-NL)", 0]], None, "mmd_tools ToonRamp 6"],

        ["ShaderNodeMath",[
            ["mmd_tools Group Input", 7],
            -0.1, #XXX
        ], {"operation": "GREATER_THAN"}, "mmd_tools Math 1"],
        ["ShaderNodeMath",[
            ["mmd_tools Group Input", 7],
            0.9,
        ], {"operation": "GREATER_THAN"}, "mmd_tools Math 2"],
        ["ShaderNodeMath",[
            ["mmd_tools Group Input", 7],
            1.9,
        ], {"operation": "GREATER_THAN"}, "mmd_tools Math 3"],
        ["ShaderNodeMath",[
            ["mmd_tools Group Input", 7],
            2.9,
        ], {"operation": "GREATER_THAN"} , "mmd_tools Math 4"],
        ["ShaderNodeMath",[
            ["mmd_tools Group Input", 7],
            3.9,
        ], {"operation": "GREATER_THAN"} , "mmd_tools Math 5"],
        ["ShaderNodeMath",[
            ["mmd_tools Group Input", 7],
            4.9,
        ], {"operation": "GREATER_THAN"} , "mmd_tools Math 6"],
        ["ShaderNodeMath",[
            ["mmd_tools Group Input", 7],
            5.9,
        ], {"operation": "GREATER_THAN"}, "mmd_tools Math 7"],

        ["ShaderNodeSeparateRGB", [["mmd_tools Group Input", 8]], None, "mmd_tools Placeholder 2"],

        ["ShaderNodeMixRGB",[
            ["mmd_tools Group Input", 9],
            [1.0, 1.0, 1.0, 1.0], # checked
            ["mmd_tools Group Input", 8],
        ],
        {"blend_type": "MIX", "use_clamp": True}, "mmd_tools ToonTex"],

        ["ShaderNodeMixRGB",[
            ["mmd_tools Math 1", 0],
            ["mmd_tools ToonTex", 0],
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
            ["mmd_tools NL", 0],
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

    def nodegroup_setup(group, node_list):

        shader = group
        nodes = shader.nodes

        for n in node_list:
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

    shader = groups.new(name='mmd_tools_shader', type='ShaderNodeTree')
    nodegroup_setup(shader, engine_shader)

    nodes = shader.nodes
    color_ramp = nodes["mmd_tools ToonRamp 1"].color_ramp
    color_ramp.interpolation = "CONSTANT"
    color_ramp.elements[0].position = 0.0
    color_ramp.elements[0].color = (1.0, 1.0, 1.0, 1.0)
    color_ramp.elements[1].position = 0.5
    color_ramp.elements[1].color = (0.803922, 0.803922, 0.803922, 1.0)

    color_ramp = nodes["mmd_tools ToonRamp 2"].color_ramp
    color_ramp.interpolation = "CONSTANT"
    color_ramp.elements[0].position = 0.0
    color_ramp.elements[0].color = (1.0, 1.0, 1.0, 1.0)
    color_ramp.elements[1].position = 0.5
    color_ramp.elements[1].color = (0.960784, 0.882353, 0.882353, 1.0)

    color_ramp = nodes["mmd_tools ToonRamp 3"].color_ramp
    color_ramp.interpolation = "CONSTANT"
    color_ramp.elements[0].position = 0.0
    color_ramp.elements[0].color = (1.0, 1.0, 1.0, 1.0)
    color_ramp.elements[1].position = 0.5
    color_ramp.elements[1].color = (0.603922, 0.603922, 0.603922, 1.0)

    color_ramp = nodes["mmd_tools ToonRamp 4"].color_ramp
    color_ramp.interpolation = "CONSTANT"
    color_ramp.elements[0].position = 0.0
    color_ramp.elements[0].color = (1.0, 1.0, 1.0, 1.0)
    color_ramp.elements[1].position = 0.5
    color_ramp.elements[1].color = (0.972549, 0.937255, 0.921569, 1.0)

    # XXX: not accurate
    color_ramp = nodes["mmd_tools ToonRamp 5"].color_ramp
    color_ramp.interpolation = "EASE"
    color_ramp.elements[0].position = 0.5
    color_ramp.elements[0].color = (1.0, 1.0, 1.0, 1.0)
    color_ramp.elements[1].position = 0.75
    color_ramp.elements[1].color = (1.0, 0.905882, 0.870588, 1.0)

    # XXX: not accurate
    color_ramp = nodes["mmd_tools ToonRamp 6"].color_ramp
    color_ramp.interpolation = "EASE"
    color_ramp.elements[0].position = 0.25 - (1.5/32.0)
    color_ramp.elements[0].color = (1.0, 0.929412, 0.380392, 1.0)
    color_ramp.elements[1].position = 0.25
    color_ramp.elements[1].color = (1.0, 0.996078, 0.94902, 1.0)
    color_ramp.elements.new(0.25 + (1.5/32.0))
    color_ramp.elements[2].color = (1.0, 0.929412, 0.380392, 1.0)
    color_ramp.elements.new(0.75 - (1.0/32.0))
    color_ramp.elements[3].color = (1.0, 0.929412, 0.380392, 1.0)
    color_ramp.elements.new(0.75 + (1.0/32.0))
    color_ramp.elements[4].color = (0.764706, 0.67451, 0.0117647, 1.0)

    shader.inputs[0].name = "Dif"
    shader.inputs[0].default_value = [1.0, 1.0, 1.0, 1.0]
    shader.inputs[1].name = "Shininess"
    shader.inputs[1].default_value = 1.0
    shader.inputs[2].name = "Spec"
    shader.inputs[2].default_value = [1.0, 1.0, 1.0, 1.0]
    shader.inputs[3].name = "Spec Weight"
    shader.inputs[3].default_value = [1.0, 1.0, 1.0, 1.0]
    shader.inputs[4].name = "Amb"
    shader.inputs[4].default_value = [0.0, 0.0, 0.0, 1.0]
    shader.inputs[5].name = "Tex"
    shader.inputs[5].default_value = [1.0, 1.0, 1.0, 1.0]
    shader.inputs[6].name = "Pure Mat"
    shader.inputs[6].default_value = [1.0, 1.0, 1.0, 1.0]
    shader.inputs[7].name = "Toon"
    shader.inputs[7].default_value = 0.0
    shader.inputs[8].name = "ToonTex"
    shader.inputs[8].default_value = [1.0, 1.0, 1.0, 1.0]
    shader.inputs[9].name = "UseToonTex"
    shader.inputs[9].default_value = 0.0

    return shader

def new_mmd_material(name, mat, ob, is_scene_update=True):
    mmd_mat = mat.mmd_material
    mat.use_transparency = True
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    ng = nodes.new("ShaderNodeGroup")
    ng.name = "mmd_tools_shader"
    ng.node_tree = mmd_shader_get()
    ng.inputs[0].default_value = list(mmd_mat.diffuse_color) + [1.0]
    ng.inputs[1].default_value = mmd_mat.shininess
    ng.inputs[2].default_value = list(mmd_mat.specular_color) + [1.0]
    ng.inputs[4].default_value = list(mmd_mat.ambient_color) + [1.0]

    mat_spw = bpy.data.materials.new(name="￥"+name+".spw")
    mat_spw.diffuse_color = (0.0, 0.0, 0.0)
    mat_spw.diffuse_intensity = 0.0
    mat_spw.specular_color = (1.0, 1.0, 1.0)
    mat_spw.specular_hardness = mmd_mat.shininess
    mat_spw.specular_shader = 'PHONG'
    if mmd_mat.shininess > 0:
        mat_spw.specular_intensity = 1.0
    else:
        mat_spw.specular_intensity = 0

    spwn = nodes.new("ShaderNodeExtendedMaterial")
    spwn.name = "Spec Weight"
    spwn.use_diffuse = False
    spwn.material = mat_spw
    mat.node_tree.links.new(ng.inputs[3], spwn.outputs[4])

    geon = nodes.new("ShaderNodeGeometry")
    geon.name = "Geo"

    geon2 = nodes.new("ShaderNodeGeometry")
    geon2.name = "Geo2"
    geon2.uv_layer = "UVMap.001"

    if mmd_mat.is_shared_toon_texture:
        ng.inputs[7].default_value = mmd_mat.toon_texture
    mat.node_tree.links.new(nodes["Output"].inputs[0], ng.outputs[0])

    amat = bpy.data.materials.new(name="￥"+name + ".alp")
    amat.diffuse_color = [1.0, 1.0, 1.0]
    amat.diffuse_intensity = 1.0
    amat.use_shadeless = True
    amat.use_transparency = True
    amat.transparency_method = 'Z_TRANSPARENCY'
    amat.alpha = mmd_mat.alpha
    amat_tex = amat.texture_slots.create(0)
    amat_tex.use_map_alpha = True
    amat_tex.texture_coords = 'UV'
    amat_tex.blend_type = 'MULTIPLY'

    an = nodes.new("ShaderNodeMaterial")
    an.name = "Alpha Mul"
    an.material = amat

    issn = nodes.new("ShaderNodeMath")
    issn.name = "Is Single"
    issn.operation = "MAXIMUM"
    mat.node_tree.links.new(issn.inputs[0], geon.outputs[8])
    issn.inputs[1].default_value = float(mmd_mat.is_double_sided)

    fan = nodes.new("ShaderNodeMath")
    fan.name = "Final Alpha"
    fan.operation = "MULTIPLY"
    mat.node_tree.links.new(fan.inputs[0], an.outputs[1])
    mat.node_tree.links.new(fan.inputs[1], issn.outputs[0])

    mat.node_tree.links.new(nodes["Output"].inputs[1], fan.outputs[0])


    mat.use_cast_buffer_shadows = mmd_mat.enabled_drop_shadow
    mat.use_cast_shadows = mmd_mat.enabled_self_shadow_map or mmd_mat.enabled_drop_shadow
    mat.use_raytrace = mmd_mat.enabled_self_shadow_map

    pmatn = nodes.new("ShaderNodeExtendedMaterial")
    pmatn.name = "Pure Mat"
    if mmd_mat.enabled_self_shadow:
        pmatn.material = bpy.data.materials["mmd_tools Node Base"]
    else:
        pmatn.material = bpy.data.materials["mmd_tools Node Base NoShadow"]
    pmatn.inputs[0].default_value = [1.0, 1.0, 1.0, 1.0]
    pmatn.inputs[1].default_value = [0.0, 0.0, 0.0, 1.0]
    pmatn.inputs[2].default_value = 1.0
    pmatn.inputs[3].default_value = [0.0, 0.0, 0.0]
    pmatn.inputs[4].default_value = [0.0, 0.0, 0.0, 1.0]
    pmatn.inputs[5].default_value = 1.0
    pmatn.inputs[6].default_value = 0.0
    pmatn.inputs[7].default_value = 1.0
    pmatn.inputs[8].default_value = 0.0
    pmatn.inputs[9].default_value = 1.0
    pmatn.inputs[10].default_value = 0.0

    mat.node_tree.links.new(ng.inputs[6], pmatn.outputs[0])

    lmatn = nodes.new("ShaderNodeExtendedMaterial")
    lmatn.name = "Lamp Data"

    lmatn.use_diffuse = True
    lmatn.use_specular = False
    lmatn.material = bpy.data.materials["mmd_tools Light Base"]
    lmatn.inputs[0].default_value = [1.0, 1.0, 1.0, 1.0]
    lmatn.inputs[1].default_value = [0.0, 0.0, 0.0, 1.0]
    lmatn.inputs[2].default_value = 1.0
    lmatn.inputs[3].default_value = [0.0, 0.0, 0.0]
    lmatn.inputs[4].default_value = [0.0, 0.0, 0.0, 1.0]
    lmatn.inputs[5].default_value = 1.0
    lmatn.inputs[6].default_value = 0.0
    lmatn.inputs[7].default_value = 1.0
    lmatn.inputs[8].default_value = 0.0
    lmatn.inputs[9].default_value = 1.0
    lmatn.inputs[10].default_value = 0.0

    lnn = nodes.new("ShaderNodeMixRGB")
    lnn.name = "LN"
    lnn.blend_type = "DIVIDE"
    lnn.inputs[0].default_value = 1.0
    mat.node_tree.links.new(lnn.inputs[1], pmatn.outputs[3])
    mat.node_tree.links.new(lnn.inputs[2], lmatn.outputs[3])

#    tvecn = nodes.new("ShaderNodeMixRGB")
#    tvecn.name = "Toon Vec Pre"
#    tvecn.blend_type = "SUBTRACT"
#    tvecn.inputs[0].default_value = 1.0
#    tvecn.inputs[1].default_value = [1.0, 1.0, 1.0, 1.0]
#    mat.node_tree.links.new(tvecn.inputs[2], lnn.outputs[0])

    tvecn2 = nodes.new("ShaderNodeMixRGB")
    tvecn2.name = "Toon Vec"
    tvecn2.blend_type = "MULTIPLY"
    tvecn2.inputs[0].default_value = 1.0
    mat.node_tree.links.new(tvecn2.inputs[1], lnn.outputs[0])
    tvecn2.inputs[2].default_value = [0.0, 1.0, 0.0, 1.0]

    ttexn = nodes.new("ShaderNodeTexture")
    ttexn.name = "Toon Tex"
    mat.node_tree.links.new(ttexn.inputs[0], tvecn2.outputs[0])


    ttex_gn = nodes.new("ShaderNodeGamma")
    ttex_gn.name = "Gamma Toon Tex"
    mat.node_tree.links.new(ttex_gn.inputs[0], ttexn.outputs[1])
    ttex_gn.inputs[1].default_value = 2.2 #???

    mat.node_tree.links.new(ng.inputs[8], ttex_gn.outputs[0])

    texn = nodes.new("ShaderNodeTexture")
    texn.name = "Tex"
    mat.node_tree.links.new(texn.inputs[0], geon.outputs[4]) # UV

    tex_gn = nodes.new("ShaderNodeGamma")
    tex_gn.name = "Gamma Tex"
    mat.node_tree.links.new(tex_gn.inputs[0], texn.outputs[1])
    tex_gn.inputs[1].default_value = 1.0 #???

    utex = nodes.new("ShaderNodeMixRGB")
    utex.name = "Use Tex"
    utex.blend_type = "MIX"
    utex.inputs[0].default_value = 0.0
    utex.inputs[1].default_value = [1.0, 1.0, 1.0, 1.0]
    mat.node_tree.links.new(utex.inputs[2], tex_gn.outputs[0])


    stexn = nodes.new("ShaderNodeTexture")
    stexn.name = "Sphere Tex"

    stex_gn = nodes.new("ShaderNodeGamma")
    stex_gn.name = "Gamma Sphere Tex"
    mat.node_tree.links.new(stex_gn.inputs[0], stexn.outputs[1])
    stex_gn.inputs[1].default_value = 1.0 #???

    ustex = nodes.new("ShaderNodeMixRGB")
    ustex.name = "Use Sphere Tex"
    ustex.blend_type = "MIX"
    ustex.inputs[0].default_value = 0.0
    ustex.inputs[1].default_value = [1.0, 1.0, 1.0, 1.0]
    mat.node_tree.links.new(ustex.inputs[2], stex_gn.outputs[0])

    mixtex = nodes.new("ShaderNodeMixRGB")
    mixtex.name = "Mix Tex"
    mixtex.blend_type = "MULTIPLY"
    mixtex.inputs[0].default_value = 1.0
    mat.node_tree.links.new(mixtex.inputs[1], utex.outputs[0])
    mat.node_tree.links.new(mixtex.inputs[2], ustex.outputs[0])

    mat.node_tree.links.new(ng.inputs[5], mixtex.outputs[0])

#    if i.texture != -1:
#        texture_slot = fnMat.create_texture(self.__textureTable[i.texture])
#        texture_slot.texture.use_mipmap = self.__use_mipmap
#        self.__imageTable[len(self.__materialTable)-1] = texture_slot.texture.image
#
#        amat_tex.texture = texture_slot.texture
#        texn.texture = texture_slot.texture
#        utex.inputs[0].default_value = 1.0

    if mmd_mat.sphere_texture_type == 1:
        mat.node_tree.links.new(stexn.inputs[0], geon.outputs[5]) # Normal
        mixtex.blend_type = "MULTIPLY"
        ustex.inputs[0].default_value = 1.0
        ustex.inputs[1].default_value = [1.0, 1.0, 1.0, 1.0]
    elif mmd_mat.sphere_texture_type == 2:
        mat.node_tree.links.new(stexn.inputs[0], geon.outputs[5]) # Normal
        mixtex.blend_type = "ADD"
        ustex.inputs[0].default_value = 1.0
        ustex.inputs[1].default_value = [0.0, 0.0, 0.0, 1.0]
    elif mmd_mat.sphere_texture_type == 3:
        mat.node_tree.links.new(stexn.inputs[0], geon2.outputs[4]) # Additional UV
        mixtex.blend_type = "MULTIPLY"
        ustex.inputs[0].default_value = 1.0
        ustex.inputs[1].default_value = [1.0, 1.0, 1.0, 1.0]

#    if i.sphere_texture != -1:
#        texture_slot = fnMat.create_sphere_texture(self.__textureTable[i.sphere_texture])
#        stexn.texture = texture_slot.texture

    edge_base_mat = bpy.data.materials.new(name="￥" + name + ".edge.base")
    edge_base_mat.use_shadeless = True
#    edge_base_mat.translucency = 1.0

    edge_mat = bpy.data.materials.new(name="￥" + name + ".edge")
    mmd_mat.edge_mat_name = edge_mat.name
    edge_mat.use_nodes = True
    edge_mat.use_transparency = True
    edge_mat.use_raytrace = False
    edge_mat.use_cast_shadows = False
    edge_mat.use_cast_buffer_shadows = False
    edge_mat.use_cast_approximate = False
    edge_mat.use_shadows = False
    edge_mat.use_ray_shadow_bias = False
    edge_mat.offset_z = 0.001 # why?
    nodes = edge_mat.node_tree.nodes

    edge_bn = nodes.new("ShaderNodeMaterial")
    edge_bn.name = "Edge Base"
    edge_bn.material = edge_base_mat
    edge_bn.inputs[0].default_value = list(mmd_mat.edge_color)[0:3] + [1.0]

    edge_mat.node_tree.links.new(nodes["Output"].inputs[0], edge_bn.outputs[0])

    edge_geon = nodes.new("ShaderNodeGeometry")
    edge_geon.name = "Geo"

    use_edge_n = nodes.new("ShaderNodeMath")
    use_edge_n.name = "Edge Alpha"
    use_edge_n.inputs[0].default_value = float(mmd_mat.enabled_toon_edge) * mmd_mat.edge_color[3]
    edge_mat.node_tree.links.new(use_edge_n.inputs[1], edge_geon.outputs[8])
    use_edge_n.operation = "MULTIPLY"

    edge_mat.node_tree.links.new(nodes["Output"].inputs[1], use_edge_n.outputs[0])

    mat_vtx = new_material_vg(name, mat, ob, is_scene_update)

    return (edge_mat, mat_vtx)

def new_material_vg(name, mat, ob, is_scene_update=True):
    mmd_mat = mat.mmd_material
    mat_vtx = ob.vertex_groups.new(name="￥" + name + ".vtx")

    edge_vtx = None
    if "edge_vtx" in ob.vertex_groups:
        edge_vtx = ob.vertex_groups["edge_vtx"]
    else:
        edge_vtx = ob.vertex_groups.new("edge_vtx")

    edge_mix = ob.modifiers.new(name="￥" + name + '.mix', type='VERTEX_WEIGHT_MIX')
    edge_mix.vertex_group_a = edge_vtx.name
    edge_mix.default_weight_a = 0.0
    edge_mix.vertex_group_b = mat_vtx.name
    edge_mix.default_weight_b = 1.0
    edge_mix.mix_set = 'B'
    edge_mix.mix_mode = 'ADD'
#    d = edge_mix.driver_new("mask_constant") # XXX: why error?
#    d.driver.expression = "bpy.data.materials['"+name+"'].mmd_material.edge_weight/100.0"
    edge_mix.mask_constant = mmd_mat.edge_weight/100.0

    mat_vg = mmd_mat.vgs.add() # XXX: not so good
    mat_vg.obj_name = ob.name
    mat_vg.vg_name = mat_vtx.name
    mat_vg.vgm_name = edge_mix.name

    cam_vtx = None
    if "cam_vtx" in ob.vertex_groups:
        cam_vtx = ob.vertex_groups["cam_vtx"]
    else:
        cam_vtx = ob.vertex_groups.new("cam_vtx") # TODO: should append all verteces as 1.0

    if not 'Camera Vtx Init' in ob.modifiers:
        cam_dist = ob.modifiers.new(name='Camera Vtx Init', type='VERTEX_WEIGHT_EDIT')
        cam_dist.vertex_group = cam_vtx.name
        cam_dist.use_add = True
        cam_dist.add_threshold = 0.0
        cam_dist.default_weight = 1.0
    elif is_scene_update: # XXX: prevent recurcive loop
        if bpy.context.scene.objects.active != ob:
            bpy.context.scene.objects.active = ob
        bpy.ops.object.modifier_move_down(modifier='Camera Vtx Init') # XXX: should move to last
        bpy.ops.object.modifier_move_down(modifier='Camera Vtx Init')
        bpy.ops.object.modifier_move_down(modifier='Camera Vtx Init')
        bpy.ops.object.modifier_move_down(modifier='Camera Vtx Init')

    if not 'Camera Distance Receiver' in ob.modifiers:
        cam_dist = ob.modifiers.new(name='Camera Distance Receiver', type='VERTEX_WEIGHT_PROXIMITY')
        cam_dist.max_dist = 1000
        cam_dist.vertex_group = cam_vtx.name
        cam_dist.target = bpy.context.scene.camera # XXX: not so good
        cam_dist.proximity_mode = 'GEOMETRY'
        cam_dist.proximity_geometry = {'VERTEX'}
        cam_dist.mask_constant = 1.0
    elif is_scene_update: # XXX: prevent recurcive loop
        if bpy.context.scene.objects.active != ob:
            bpy.context.scene.objects.active = ob
        bpy.ops.object.modifier_move_down(modifier='Camera Distance Receiver') # XXX: should move to last
        bpy.ops.object.modifier_move_down(modifier='Camera Distance Receiver')
        bpy.ops.object.modifier_move_down(modifier='Camera Distance Receiver')
        bpy.ops.object.modifier_move_down(modifier='Camera Distance Receiver')

    cam_mix = None
    if not 'Camera Distance Mixer' in ob.modifiers:
        cam_mix = ob.modifiers.new(name='Camera Distance Mixer', type='VERTEX_WEIGHT_MIX')
        cam_mix.vertex_group_a = edge_vtx.name
        cam_mix.default_weight_a = 0.0
        cam_mix.vertex_group_b = cam_vtx.name
        cam_mix.default_weight_b = 1.0
        cam_mix.mix_mode = 'MUL'
        cam_mix.mix_set = 'ALL'
        cam_mix.mask_constant = 1.0
    elif is_scene_update: # XXX: prevent recurcive loop
        if bpy.context.scene.objects.active != ob:
            bpy.context.scene.objects.active = ob
        bpy.ops.object.modifier_move_down(modifier='Camera Distance Mixer') # XXX: should move to last
        bpy.ops.object.modifier_move_down(modifier='Camera Distance Mixer')
        bpy.ops.object.modifier_move_down(modifier='Camera Distance Mixer')
        bpy.ops.object.modifier_move_down(modifier='Camera Distance Mixer')

    edge_mod = None
    if not 'Edge Solidify' in ob.modifiers:
        edge_mod = ob.modifiers.new(name='Edge Solidify', type='SOLIDIFY')
        edge_mod.offset = 1.0
        edge_mod.thickness = 2 * 100.0 # XXX: why?
        edge_mod.thickness_clamp = 0.001 # XXX: why?
        edge_mod.use_rim = False
        edge_mod.material_offset = 1
        edge_mod.use_flip_normals = True
        edge_mod.vertex_group = edge_vtx.name
    elif is_scene_update: # XXX: prevent recurcive loop
        if bpy.context.scene.objects.active != ob:
            bpy.context.scene.objects.active = ob
        bpy.ops.object.modifier_move_down(modifier='Edge Solidify') # XXX: should move to last
        bpy.ops.object.modifier_move_down(modifier='Edge Solidify')
        bpy.ops.object.modifier_move_down(modifier='Edge Solidify')
        bpy.ops.object.modifier_move_down(modifier='Edge Solidify')

    return mat_vtx

# multi assigning also works
def mmd_mat_vg_update(ob, is_scene_update=True):

    # update weight groups and modifiers
    vgs_idx = [-1] * len(ob.material_slots)
    mat_used_num = {}
    for i, m in enumerate(ob.material_slots):
        if not m.material or m.material.name.find(".edge")>=0:
            continue

        if not m.material in mat_used_num:
            mat_used_num[m.material] = 0
        else:
            mat_used_num[m.material] += 1

        n = mat_used_num[m.material]
        for j, vg in enumerate(m.material.mmd_material.vgs):
            if vg.obj_name != ob.name:
                continue
            if not vg.vgm_name in ob.modifiers or \
               not vg.vg_name in ob.vertex_groups: # unbundled
                m.material.mmd_material.vgs.remove(j)
                continue
            if n == 0:
                vgs_idx[i] = j
            if n < 0:
                m.material.mmd_material.vgs.remove(j)
            n -= 1
        while n > 0 or vgs_idx[i] == -1:
            new_material_vg(m.material.name, m.material, ob, is_scene_update)
            vgs_idx[i] = len(m.material.mmd_material.vgs) -1
            n -= 1

    for mod in ob.modifiers:
        if mod.type != 'VERTEX_WEIGHT_MIX' or mod.name.find(".mix") < 0:
            continue
        mod_used = False
        for i, m in enumerate(ob.material_slots):
            if not m.material or m.material.name.find(".edge")>=0:
                continue
            if mod.name == m.material.mmd_material.vgs[vgs_idx[i]].vgm_name:
                mod_used = True

        if not mod_used:
            ob.modifiers.remove(mod)

    for ovg in ob.vertex_groups:
        if ovg.name.find(".vtx") < 0:
            continue
        ovg_used = False
        for i, m in enumerate(ob.material_slots):
            if not m.material or m.material.name.find(".edge")>=0:
                continue
            if ovg.name == m.material.mmd_material.vgs[vgs_idx[i]].vg_name:
                ovg_used = True

        if not ovg_used:
            ob.vertex_groups.remove(ovg)

    # update weights
    mode = bpy.context.active_object.mode

    if mode == 'EDIT':
        bpy.ops.object.mode_set(mode='OBJECT')

    for i, m in enumerate(ob.material_slots):
        if not m.material or m.material.name.find(".edge") >= 0:
            continue
#        for j in m.material.mmd_material.vgs:
#            if j.obj_name != ob.name:
#                continue
#            vg = ob.vertex_groups[j.vg_name]
#            verts = [v for f in ob.data.polygons if f.material_index == i for v in f.vertices]
#            vg.add(verts, 1.0, 'REPLACE')

        vg = ob.vertex_groups[m.material.mmd_material.vgs[vgs_idx[i]].vg_name]
        verts = [v for f in ob.data.polygons if f.material_index == i for v in f.vertices]
        vg.add(verts, 1.0, 'REPLACE')

    if mode == 'EDIT':
        bpy.ops.object.mode_set(mode='EDIT')

