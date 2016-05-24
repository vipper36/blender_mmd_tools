# -*- coding: utf-8 -*-
import os
import collections
import logging
import time
import re

import bpy
import mathutils

import mmd_tools.core.model as mmd_model
import mmd_tools.core.pmx as pmx
from mmd_tools.core.material import FnMaterial
from mmd_tools import utils
from mmd_tools import bpyutils
from mmd_tools.core.vmd.importer import VMDImporter


class PMXImporter:
    TO_BLE_MATRIX = mathutils.Matrix([
        [1.0, 0.0, 0.0, 0.0],
        [0.0, 0.0, 1.0, 0.0],
        [0.0, 1.0, 0.0, 0.0],
        [0.0, 0.0, 0.0, 1.0]])
    CATEGORIES = {
        0: 'SYSTEM',
        1: 'EYEBROW',
        2: 'EYE',
        3: 'MOUTH',
        }
    MORPH_TYPES = {
        0: 'group_morphs',
        1: 'vertex_morphs',
        2: 'bone_morphs',
        3: 'uv_morphs',
        4: 'uv_morphs',
        5: 'uv_morphs',
        6: 'uv_morphs',
        7: 'uv_morphs',
        8: 'material_morphs',
        }

    def __init__(self):
        self.__model = None
        self.__targetScene = bpy.context.scene

        self.__scale = None

        self.__root = None
        self.__armObj = None
        self.__meshObj = None

        self.__vertexGroupTable = None
        self.__textureTable = None

        self.__boneTable = []
        self.__rigidTable = []
        self.__materialTable = []
        self.__imageTable = {}

        self.__materialFaceCountTable = None

    @staticmethod
    def flipUV_V(uv):
        u, v = uv
        return [u, 1.0-v]

    def __getMaterialIndexFromFaceIndex(self, face_index):
        count = 0
        for i, c in enumerate(self.__materialFaceCountTable):
            if face_index < count + c:
                return i
            count += c
        raise Exception('invalid face index.')

    def __createObjects(self):
        """ Create main objects and link them to scene.
        """
        pmxModel = self.__model
        self.__rig = mmd_model.Model.create(pmxModel.name, pmxModel.name_e, self.__scale)
        mmd_root = self.__rig.rootObject().mmd_root
        txt = bpy.data.texts.new(pmxModel.name+'_comment')
        txt.from_string(pmxModel.comment.replace('\r', ''))
        txt.current_line_index = 0
        mmd_root.comment_text = txt.name
        txt = bpy.data.texts.new(pmxModel.name+'_comment_e')
        txt.from_string(pmxModel.comment_e.replace('\r', ''))
        txt.current_line_index = 0
        mmd_root.comment_e_text = txt.name

        self.__armObj = self.__rig.armature()
        self.__armObj.hide = True
        
        # Temporarily set the root object as active to let property function hooks access it.
        self.__targetScene.objects.active = self.__rig.rootObject()

    def __createMeshObject(self):
        model_name = self.__model.name
        self.__meshObj = bpy.data.objects.new(name=model_name+'_mesh', object_data=bpy.data.meshes.new(name=model_name))
        self.__meshObj.parent = self.__armObj
        self.__targetScene.objects.link(self.__meshObj)

    def __importVertexGroup(self):
        self.__vertexGroupTable = []
        for i in self.__model.bones:
            self.__vertexGroupTable.append(self.__meshObj.vertex_groups.new(name=i.name))

    def __importVertices(self):
        self.__importVertexGroup()

        pmxModel = self.__model
        mesh = self.__meshObj.data

        mesh.vertices.add(count=len(self.__model.vertices))
        for i, pv in enumerate(pmxModel.vertices):
            bv = mesh.vertices[i]

            bv.co = mathutils.Vector(pv.co) * self.TO_BLE_MATRIX * self.__scale
            #bv.normal = pv.normal # no effect

            if isinstance(pv.weight.weights, pmx.BoneWeightSDEF):
                self.__vertexGroupTable[pv.weight.bones[0]].add(index=[i], weight=pv.weight.weights.weight, type='REPLACE')
                self.__vertexGroupTable[pv.weight.bones[1]].add(index=[i], weight=1.0-pv.weight.weights.weight, type='REPLACE')
            elif len(pv.weight.bones) == 1:
                bone_index = pv.weight.bones[0]
                if bone_index >= 0:
                    self.__vertexGroupTable[bone_index].add(index=[i], weight=1.0, type='REPLACE')
            elif len(pv.weight.bones) == 2:
                self.__vertexGroupTable[pv.weight.bones[0]].add(index=[i], weight=pv.weight.weights[0], type='REPLACE')
                self.__vertexGroupTable[pv.weight.bones[1]].add(index=[i], weight=1.0-pv.weight.weights[0], type='REPLACE')
            elif len(pv.weight.bones) == 4:
                # If two or more weights for the same bone is present, the second and subsequent will be ignored.
                for bone, weight in reversed([x for x in zip(pv.weight.bones, pv.weight.weights) if x[0] >= 0]):
                    self.__vertexGroupTable[bone].add(index=[i], weight=weight, type='REPLACE')
            else:
                raise Exception('unkown bone weight type.')

    def __importTextures(self):
        pmxModel = self.__model

        self.__textureTable = []
        for i in pmxModel.textures:
            self.__textureTable.append(bpy.path.resolve_ncase(path=i.path))

    def __createEditBones(self, obj, pmx_bones):
        """ create EditBones from pmx file data.
        @return the list of bone names which can be accessed by the bone index of pmx data.
        """
        editBoneTable = []
        nameTable = []
        dependency_cycle_ik_bones = []
        #for i, p_bone in enumerate(pmx_bones):
        #    if p_bone.isIK:
        #        if p_bone.target != -1:
        #            t = pmx_bones[p_bone.target]
        #            if p_bone.parent == t.parent:
        #                dependency_cycle_ik_bones.append(i)

        with bpyutils.edit_object(obj) as data:
            for i in pmx_bones:
                bone = data.edit_bones.new(name=i.name)
                loc = mathutils.Vector(i.location) * self.__scale * self.TO_BLE_MATRIX
                bone.head = loc
                editBoneTable.append(bone)
                nameTable.append(bone.name)

            for i, (b_bone, m_bone) in enumerate(zip(editBoneTable, pmx_bones)):
                if m_bone.parent != -1:
                    if i not in dependency_cycle_ik_bones:
                        b_bone.parent = editBoneTable[m_bone.parent]
                    else:
                        b_bone.parent = editBoneTable[m_bone.parent].parent

            for b_bone, m_bone in zip(editBoneTable, pmx_bones):
                if isinstance(m_bone.displayConnection, int):
                    if m_bone.displayConnection != -1:
                        b_bone.tail = editBoneTable[m_bone.displayConnection].head
                    else:
                        b_bone.tail = b_bone.head
                else:
                    loc = mathutils.Vector(m_bone.displayConnection) * self.TO_BLE_MATRIX * self.__scale
                    b_bone.tail = b_bone.head + loc

            for b_bone, m_bone in zip(editBoneTable, pmx_bones):
                if isinstance(m_bone.displayConnection, int)\
                        and m_bone.displayConnection >= 0\
                        and not m_bone.isMovable:
                    t = editBoneTable[m_bone.displayConnection]
                    if t.parent is not None and t.parent == b_bone:
                        t.use_connect = True

            for b_bone, m_bone in zip(editBoneTable, pmx_bones):
                # Set the length of too short bones to 1 because Blender delete them.
                if b_bone.length < 0.001:
                    loc = mathutils.Vector([0, 0, 1]) * self.__scale
                    b_bone.tail = b_bone.head + loc
                    if m_bone.displayConnection != -1 and m_bone.displayConnection != [0.0, 0.0, 0.0]:
                        logging.debug(' * set as tip bone %s, display %s', b_bone.name, str(m_bone.displayConnection))
                        m_bone.displayConnection = -1

        return nameTable

    def __sortPoseBonesByBoneIndex(self, pose_bones, bone_names):
        r = []
        for i in bone_names:
            r.append(pose_bones[i])
        return r

    def __applyIk(self, index, pmx_bone, pose_bones):
        """ create a IK bone constraint
         If the IK bone and the target bone is separated, a dummy IK target bone is created as a child of the IK bone.
         @param index the bone index
         @param pmx_bone pmx.Bone
         @param pose_bones the list of PoseBones sorted by the bone index
        """

        ik_bone = pose_bones[pmx_bone.target].parent
        target_bone = pose_bones[index]

        ikConst = self.__rig.create_ik_constraint(ik_bone, target_bone)
        ikConst.iterations = pmx_bone.loopCount
        ikConst.chain_count = len(pmx_bone.ik_links)
        for i in pmx_bone.ik_links:
            if i.maximumAngle is not None:
                bone = pose_bones[i.target]
                bone.use_ik_limit_x = True
                bone.use_ik_limit_y = True
                bone.use_ik_limit_z = True
                bone.ik_max_x = -i.minimumAngle[0]
                bone.ik_max_y = i.maximumAngle[1]
                bone.ik_max_z = i.maximumAngle[2]
                bone.ik_min_x = -i.maximumAngle[0]
                bone.ik_min_y = i.minimumAngle[1]
                bone.ik_min_z = i.minimumAngle[2]


    def __importBones(self):
        pmxModel = self.__model

        boneNameTable = self.__createEditBones(self.__armObj, pmxModel.bones)
        pose_bones = self.__sortPoseBonesByBoneIndex(self.__armObj.pose.bones, boneNameTable)
        self.__boneTable = pose_bones
        for i, pmx_bone in sorted(enumerate(pmxModel.bones), key=lambda x: x[1].transform_order):
            b_bone = pose_bones[i]
            b_bone.mmd_bone.name_j = pmx_bone.name
            b_bone.mmd_bone.name_e = pmx_bone.name_e
            b_bone.mmd_bone.transform_order = pmx_bone.transform_order
            b_bone.mmd_bone.is_visible = pmx_bone.visible
            b_bone.mmd_bone.is_controllable = pmx_bone.isControllable
            b_bone.mmd_bone.transform_after_dynamics = pmx_bone.transAfterPhis

            if pmx_bone.displayConnection == -1 or pmx_bone.displayConnection == [0.0, 0.0, 0.0]:                
                b_bone.mmd_bone.is_tip = True
                logging.debug('bone %s is a tip bone', pmx_bone.name)
            elif not isinstance(pmx_bone.displayConnection, int):
                b_bone.mmd_bone.use_tail_location = True
                logging.debug('bone %s is using a vector tail', pmx_bone.name)
            else:
                logging.debug('bone %s is not using a vector tail and is not a tip bone. DisplayConnection: %s', 
                              pmx_bone.name, str(pmx_bone.displayConnection))
                
            if pmx_bone.axis is not None and pmx_bone.parent != -1:
                #The twist bones (type 8 in PMD) are special, without this the tail will not be displayed during export
                pose_bones[pmx_bone.parent].mmd_bone.use_tail_location = True
                                
            #Movable bones should have a tail too
            if pmx_bone.isMovable and pmx_bone.visible:
                b_bone.mmd_bone.use_tail_location = True

            #Some models don't have correct tail bones, let's try to fix it
            #if re.search(u'先$', pmx_bone.name):
            #    b_bone.mmd_bone.is_tip = True

            b_bone.bone.hide = b_bone.mmd_bone.is_tip or not pmx_bone.visible

            if not pmx_bone.isRotatable:
                b_bone.lock_rotation = [True, True, True]

            if not pmx_bone.isMovable:
                b_bone.lock_location = [True, True, True]

            if pmx_bone.isIK:
                if pmx_bone.target != -1:
                    self.__applyIk(i, pmx_bone, pose_bones)

            if pmx_bone.hasAdditionalRotate or pmx_bone.hasAdditionalLocation:
                bone_index, influ = pmx_bone.additionalTransform
                mmd_bone = b_bone.mmd_bone
                mmd_bone.has_additional_rotation = pmx_bone.hasAdditionalRotate
                mmd_bone.has_additional_location = pmx_bone.hasAdditionalLocation
                mmd_bone.additional_transform_influence = influ
                if 0 <= bone_index < len(pose_bones):
                    mmd_bone.additional_transform_bone = pose_bones[bone_index].name

            if pmx_bone.localCoordinate is not None:
                b_bone.mmd_bone.enabled_local_axes = True
                b_bone.mmd_bone.local_axis_x = pmx_bone.localCoordinate.x_axis
                b_bone.mmd_bone.local_axis_z = pmx_bone.localCoordinate.z_axis

            if pmx_bone.axis is not None:
                b_bone.mmd_bone.enabled_fixed_axis = True
                b_bone.mmd_bone.fixed_axis=pmx_bone.axis

            #if b_bone.mmd_bone.is_tip:
            #    b_bone.lock_rotation = [True, True, True]
            #    b_bone.lock_location = [True, True, True]
            #    b_bone.lock_scale = [True, True, True]

    def __importRigids(self):
        self.__rigidTable = []
        start_time = time.time()
        for rigid in self.__model.rigids:
            loc = mathutils.Vector(rigid.location) * self.TO_BLE_MATRIX * self.__scale
            rot = mathutils.Vector(rigid.rotation) * self.TO_BLE_MATRIX * -1
            if rigid.type == pmx.Rigid.TYPE_BOX:
                size = mathutils.Vector(rigid.size) * self.TO_BLE_MATRIX
            else:
                size = mathutils.Vector(rigid.size)

            obj = self.__rig.createRigidBody(
                name = rigid.name,
                name_e = rigid.name_e,
                shape_type = rigid.type,
                dynamics_type = rigid.mode,
                location = loc,
                rotation = rot,
                size = size * self.__scale,
                collision_group_number = rigid.collision_group_number,
                collision_group_mask = [rigid.collision_group_mask & (1<<i) == 0 for i in range(16)],
                arm_obj = self.__armObj,
                mass=rigid.mass,
                friction = rigid.friction,
                angular_damping = rigid.rotation_attenuation,
                linear_damping = rigid.velocity_attenuation,
                bounce = rigid.bounce,
                bone = None if rigid.bone == -1 or rigid.bone is None else self.__boneTable[rigid.bone].name,
                )
            obj.hide = True
            self.__rigidTable.append(obj)

        logging.debug('Finished importing rigid bodies in %f seconds.', time.time() - start_time)


    def __importJoints(self):
        for joint in self.__model.joints:
            loc = mathutils.Vector(joint.location) * self.TO_BLE_MATRIX * self.__scale
            rot = mathutils.Vector(joint.rotation) * self.TO_BLE_MATRIX * -1

            obj = self.__rig.createJoint(
                name = joint.name,
                name_e = joint.name_e,
                location = loc,
                rotation = rot,
                size = 0.5 * self.__scale,
                rigid_a = self.__rigidTable[joint.src_rigid],
                rigid_b = self.__rigidTable[joint.dest_rigid],
                maximum_location = mathutils.Vector(joint.maximum_location) * self.TO_BLE_MATRIX * self.__scale,
                minimum_location = mathutils.Vector(joint.minimum_location) * self.TO_BLE_MATRIX * self.__scale,
                maximum_rotation = mathutils.Vector(joint.minimum_rotation) * self.TO_BLE_MATRIX * -1,
                minimum_rotation = mathutils.Vector(joint.maximum_rotation) * self.TO_BLE_MATRIX * -1,
                spring_linear = mathutils.Vector(joint.spring_constant) * self.TO_BLE_MATRIX,
                spring_angular = mathutils.Vector(joint.spring_rotation_constant) * self.TO_BLE_MATRIX,
                )
            obj.hide = True


    def __importMaterials(self):
        self.__importTextures()

        pmxModel = self.__model

        self.__materialFaceCountTable = []
        for i in pmxModel.materials:
            mat = bpy.data.materials.new(name=i.name)
            self.__materialTable.append(mat)
            mmd_mat = mat.mmd_material
            mat.use_nodes = True
            nodes = mat.node_tree.nodes
            ng = nodes.new("ShaderNodeGroup")
            ng.name = "mmd_tools_shader"
            ng.node_tree = bpy.data.node_groups["mmd_tools_shader"]
            ng.inputs[0].default_value = i.diffuse[0:3] + [1.0]
            ng.inputs[1].default_value = i.specular + [1.0]
            ng.inputs[3].default_value = i.ambient + [1.0]

            mat_spw = bpy.data.materials.new(name=i.name+".spw")
            mat_spw.diffuse_color = (0.0, 0.0, 0.0)
            mat_spw.diffuse_intensity = 0.0
            mat_spw.specular_color = (1.0, 1.0, 1.0)
            mat_spw.specular_hardness = i.shininess
            if i.shininess > 0:
                mat_spw.specular_intensity = 0.2
            else:
                mat_spw.specular_intensity = 0

            spwn = nodes.new("ShaderNodeExtendedMaterial")
            spwn.name = "Spec Weight"
            spwn.use_diffuse = False
            spwn.material = mat_spw
            mat.node_tree.links.new(ng.inputs[2], spwn.outputs[0])

            geon = nodes.new("ShaderNodeGeometry")
            geon.name = "Geo"

            geon2 = nodes.new("ShaderNodeGeometry")
            geon2.name = "Geo2"
            geon2.uv_layer = "UVMap.001"

            if i.is_shared_toon_texture:
                ng.inputs[5].default_value = i.toon_texture
            mat.node_tree.links.new(nodes["Output"].inputs[0], ng.outputs[0])

            mat.alpha = i.diffuse[3]
            if mat.alpha < 1.0 or mat.specular_alpha < 1.0 or i.texture != -1:
                mat.use_transparency = True
                mat.transparency_method = 'Z_TRANSPARENCY'

            mmd_mat.name_j = i.name
            mmd_mat.name_e = i.name_e
            mmd_mat.ambient_color = i.ambient
            mmd_mat.diffuse_color = i.diffuse[0:3]
            mmd_mat.alpha = i.diffuse[3]
            mmd_mat.specular_color = i.specular
            mmd_mat.shininess = i.shininess
            mmd_mat.is_double_sided = i.is_double_sided
            mmd_mat.enabled_drop_shadow = i.enabled_drop_shadow
            mmd_mat.enabled_self_shadow_map = i.enabled_self_shadow_map
            mmd_mat.enabled_self_shadow = i.enabled_self_shadow
            mmd_mat.enabled_toon_edge = i.enabled_toon_edge
            mmd_mat.edge_color = i.edge_color
            mmd_mat.edge_weight = i.edge_size
            mmd_mat.sphere_texture_type = str(i.sphere_texture_mode)

            pmatn = nodes.new("ShaderNodeExtendedMaterial")
            pmatn.name = "Pure Mat"
            pmatn.material = bpy.data.materials["mmd_tools Node Base"]
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

            tvecn = nodes.new("ShaderNodeMixRGB")
            tvecn.name = "Toon Vec Pre"
            tvecn.blend_type = "MULTIPLY"
            tvecn.inputs[0].default_value = 1.0
            mat.node_tree.links.new(tvecn.inputs[1], pmatn.outputs[0])
            tvecn.inputs[2].default_value = [0.0, 1.0, 0.0, 0.0]

            tvecn2 = nodes.new("ShaderNodeMixRGB")
            tvecn2.name = "Toon Vec"
            tvecn2.blend_type = "SUBTRACT"
            tvecn2.inputs[0].default_value = 1.0
            mat.node_tree.links.new(tvecn2.inputs[1], tvecn.outputs[0])
            tvecn2.inputs[2].default_value = [0.0, 0.5, 0.0, 0.0]

            ttexn = nodes.new("ShaderNodeTexture")
            ttexn.name = "Toon Tex"
            mat.node_tree.links.new(ttexn.inputs[0], tvecn2.outputs[0])

            mat.node_tree.links.new(ng.inputs[6], ttexn.outputs[1])

            if i.is_shared_toon_texture:
                mmd_mat.is_shared_toon_texture = True
                mmd_mat.shared_toon_texture = i.toon_texture
            else:
                mmd_mat.is_shared_toon_texture = False
                mmd_mat.shared_toon_texture = -1.0
                if i.toon_texture >= 0:
                    mmd_mat.toon_texture = self.__textureTable[i.toon_texture]
#                    ttexn.texture = XXX
                    ng.inputs[7].default_value = 1.0
                else:
                    mmd_mat.toon_texture = ''
#                    ttexn.texture = None
                    ng.inputs[7].default_value = 0.0
            mmd_mat.comment = i.comment

            self.__materialFaceCountTable.append(int(i.vertex_count/3))
            self.__meshObj.data.materials.append(mat)
            fnMat = FnMaterial(mat)

            texn = nodes.new("ShaderNodeTexture")
            texn.name = "Tex"
            mat.node_tree.links.new(texn.inputs[0], geon.outputs[4]) # UV

            utex = nodes.new("ShaderNodeMixRGB")
            utex.name = "Use Tex"
            utex.blend_type = "MIX"
            utex.inputs[0].default_value = 0.0
            utex.inputs[1].default_value = [1.0, 1.0, 1.0, 1.0]
            mat.node_tree.links.new(utex.inputs[2], texn.outputs[1])

            stexn = nodes.new("ShaderNodeTexture")
            stexn.name = "Sphere Tex"

            ustex = nodes.new("ShaderNodeMixRGB")
            ustex.name = "Use Sphere Tex"
            ustex.blend_type = "MIX"
            ustex.inputs[0].default_value = 0.0
            ustex.inputs[1].default_value = [1.0, 1.0, 1.0, 1.0]
            mat.node_tree.links.new(ustex.inputs[2], stexn.outputs[1])

            mixtex = nodes.new("ShaderNodeMixRGB")
            mixtex.name = "Mix Tex"
            mixtex.blend_type = "MULTIPLY"
            mixtex.inputs[0].default_value = 1.0
            mat.node_tree.links.new(mixtex.inputs[1], utex.outputs[0])
            mat.node_tree.links.new(mixtex.inputs[2], ustex.outputs[0])

            mat.node_tree.links.new(ng.inputs[4], mixtex.outputs[0])

            if i.texture != -1:
                texture_slot = fnMat.create_texture(self.__textureTable[i.texture])
                texture_slot.texture.use_mipmap = self.__use_mipmap
                self.__imageTable[len(self.__materialTable)-1] = texture_slot.texture.image

                texn.texture = texture_slot.texture
                utex.inputs[0].default_value = 1.0

            if i.sphere_texture_mode == 1:
#                amount = self.__sph_blend_factor
                mat.node_tree.links.new(stexn.inputs[0], geon.outputs[5]) # Normal
                mixtex.blend_type = "MULTIPLY"
                ustex.inputs[0].default_value = 1.0
                ustex.inputs[1].default_value = [1.0, 1.0, 1.0, 1.0]
            elif i.sphere_texture_mode == 2:
#                amount = self.__spa_blend_factor
                mat.node_tree.links.new(stexn.inputs[0], geon.outputs[5]) # Normal
                mixtex.blend_type = "ADD"
                ustex.inputs[0].default_value = 1.0
                ustex.inputs[1].default_value = [0.0, 0.0, 0.0, 1.0]
            elif i.sphere_texture_mode == 3:
                mat.node_tree.links.new(stexn.inputs[0], geon2.outputs[4]) # Additional UV
                mixtex.blend_type = "MULTIPLY"
                ustex.inputs[0].default_value = 1.0
                ustex.inputs[1].default_value = [1.0, 1.0, 1.0, 1.0]

            if i.sphere_texture != -1: # and amount != 0.0
                texture_slot = fnMat.create_sphere_texture(self.__textureTable[i.sphere_texture])
                stexn.texture = texture_slot.texture
#                texture_slot.diffuse_color_factor = amount

    def __importFaces(self):
        pmxModel = self.__model
        mesh = self.__meshObj.data

        mesh.tessfaces.add(len(pmxModel.faces))
        uvLayer = mesh.tessface_uv_textures.new()
        uvLayer2 = mesh.tessface_uv_textures.new()
        for i, f in enumerate(pmxModel.faces):
            bf = mesh.tessfaces[i]
            bf.vertices_raw = list(f) + [0]
            bf.use_smooth = True

            uv = uvLayer.data[i]
            uv.uv1 = self.flipUV_V(pmxModel.vertices[f[0]].uv)
            uv.uv2 = self.flipUV_V(pmxModel.vertices[f[1]].uv)
            uv.uv3 = self.flipUV_V(pmxModel.vertices[f[2]].uv)

            uv2 = uvLayer2.data[i]
            uv2.uv1 = self.flipUV_V(pmxModel.vertices[f[0]].additional_uvs[0][0:2])
            uv2.uv2 = self.flipUV_V(pmxModel.vertices[f[1]].additional_uvs[0][0:2])
            uv2.uv3 = self.flipUV_V(pmxModel.vertices[f[2]].additional_uvs[0][0:2])

            bf.material_index = self.__getMaterialIndexFromFaceIndex(i)
            uv.image = self.__imageTable.get(bf.material_index, None)
            #uv2.image = # XXX: TODO

    def __importVertexMorphs(self):
        pmxModel = self.__model
        mmd_root = self.__rig.rootObject().mmd_root
        utils.selectAObject(self.__meshObj)
        bpy.ops.object.shape_key_add()
        categories = self.CATEGORIES
        for morph in filter(lambda x: isinstance(x, pmx.VertexMorph), pmxModel.morphs):
            shapeKey = self.__meshObj.shape_key_add(morph.name)
            vtx_morph = mmd_root.vertex_morphs.add()
            vtx_morph.name = morph.name
            vtx_morph.name_e = morph.name_e
            vtx_morph.category = categories.get(morph.category, 'OTHER')
            for md in morph.offsets:
                shapeKeyPoint = shapeKey.data[md.index]
                offset = mathutils.Vector(md.offset) * self.TO_BLE_MATRIX
                shapeKeyPoint.co = shapeKeyPoint.co + offset * self.__scale

    def __importMaterialMorphs(self):
        mmd_root = self.__rig.rootObject().mmd_root
        categories = self.CATEGORIES
        for morph in [x for x in self.__model.morphs if isinstance(x, pmx.MaterialMorph)]:
            mat_morph = mmd_root.material_morphs.add()
            mat_morph.name = morph.name
            mat_morph.name_e = morph.name_e
            mat_morph.category = categories.get(morph.category, 'OTHER')
            for morph_data in morph.offsets:
                if not (0 <= morph_data.index < len(self.__materialTable)):
                    continue
                data = mat_morph.data.add()
                data.related_mesh = self.__meshObj.data.name
                data.material = self.__materialTable[morph_data.index].name
                data.offset_type = ['MULT', 'ADD'][morph_data.offset_type]
                data.diffuse_color = morph_data.diffuse_offset
                data.specular_color = morph_data.specular_offset
                data.shininess = morph_data.shininess_offset
                data.ambient_color = morph_data.ambient_offset
                data.edge_color = morph_data.edge_color_offset
                data.edge_weight = morph_data.edge_size_offset
                data.texture_factor = morph_data.texture_factor
                data.sphere_texture_factor = morph_data.sphere_texture_factor
                data.toon_texture_factor = morph_data.toon_texture_factor

    def __importBoneMorphs(self):
        mmd_root = self.__rig.rootObject().mmd_root
        categories = self.CATEGORIES
        for morph in [x for x in self.__model.morphs if isinstance(x, pmx.BoneMorph)]:
            bone_morph = mmd_root.bone_morphs.add()
            bone_morph.name = morph.name
            bone_morph.name_e = morph.name_e
            bone_morph.category = categories.get(morph.category, 'OTHER')
            for morph_data in morph.offsets:
                if not (0 <= morph_data.index < len(self.__boneTable)):
                    continue
                data = bone_morph.data.add()
                bl_bone = self.__boneTable[morph_data.index]
                data.bone = bl_bone.name
                mat = VMDImporter.makeVMDBoneLocationToBlenderMatrix(bl_bone)
                data.location = mat * mathutils.Vector(morph_data.location_offset) * self.__scale
                data.rotation = VMDImporter.convertVMDBoneRotationToBlender(bl_bone, morph_data.rotation_offset)

    def __importUVMorphs(self):
        mmd_root = self.__rig.rootObject().mmd_root
        categories = self.CATEGORIES
        for morph in [x for x in self.__model.morphs if isinstance(x, pmx.UVMorph)]:
            uv_morph = mmd_root.uv_morphs.add()
            uv_morph.name = morph.name
            uv_morph.name_e = morph.name_e
            uv_morph.category = categories.get(morph.category, 'OTHER')
            uv_morph.uv_index = morph.uv_index
            for morph_data in morph.offsets:
                idx = morph_data.index
                dx, dy, dz, dw = morph_data.offset
                data = uv_morph.data.add()
                data.index = idx
                data.offset = (dx, -dy, dz, dw) # dz, dw are not used

    def __importGroupMorphs(self):
        mmd_root = self.__rig.rootObject().mmd_root
        categories = self.CATEGORIES
        morph_types = self.MORPH_TYPES
        pmx_morphs = self.__model.morphs
        for morph in [x for x in pmx_morphs if isinstance(x, pmx.GroupMorph)]:
            group_morph = mmd_root.group_morphs.add()
            group_morph.name = morph.name
            group_morph.name_e = morph.name_e
            group_morph.category = categories.get(morph.category, 'OTHER')
            for morph_data in morph.offsets:
                if not (0 <= morph_data.morph < len(pmx_morphs)):
                    continue
                data = group_morph.data.add()
                m = pmx_morphs[morph_data.morph]
                data.name = m.name
                data.morph_type = morph_types[m.type_index()]
                data.factor = morph_data.factor

    def __importDisplayFrames(self):
        pmxModel = self.__model
        root = self.__rig.rootObject()
        morph_types = self.MORPH_TYPES

        for i in pmxModel.display:
            frame = root.mmd_root.display_item_frames.add()
            frame.name = i.name
            frame.name_e = i.name_e
            frame.is_special = i.isSpecial
            for disp_type, index in i.data:
                item = frame.items.add()
                if disp_type == 0:
                    item.type = 'BONE'
                    item.name = self.__boneTable[index].name
                elif disp_type == 1:
                    item.type = 'MORPH'
                    morph = pmxModel.morphs[index]
                    item.name = morph.name
                    item.morph_type = morph_types[morph.type_index()]
                else:
                    raise Exception('Unknown display item type.')

    def __addArmatureModifier(self, meshObj, armObj):
        armModifier = meshObj.modifiers.new(name='Armature', type='ARMATURE')
        armModifier.object = armObj
        armModifier.use_vertex_groups = True

    def __assignCustomNormals(self):
        mesh = self.__meshObj.data
        if not hasattr(mesh, 'has_custom_normals'):
            logging.info(' * No support for custom normals!!')
            return
        logging.info('Setting custom normals!!')
        custom_normals = [(mathutils.Vector(v.normal).xzy).normalized() for v in self.__model.vertices]
        mesh.normals_split_custom_set_from_vertices(custom_normals)
        mesh.use_auto_smooth = True
        logging.info('   - Done!!')

    def __renameLRBones(self):
        pose_bones = self.__armObj.pose.bones
        for i in pose_bones:
            if i.is_mmd_shadow_bone:
                continue
            self.__rig.renameBone(i.name, utils.convertNameToLR(i.name))
            # self.__meshObj.vertex_groups[i.mmd_bone.name_j].name = i.name

    def __fixRepeatedMorphName(self):
        used_names_map = {}
        for m in self.__model.morphs:
            #used_names = used_names_map.setdefault('all', set())
            used_names = used_names_map.setdefault(type(m), set())
            m.name = utils.uniqueName(m.name, used_names)
            used_names.add(m.name)

    def execute(self, **args):
        if 'pmx' in args:
            self.__model = args['pmx']
        else:
            self.__model = pmx.load(args['filepath'])
        self.__fixRepeatedMorphName()

        types = args.get('types', set())
        self.__scale = args.get('scale', 1.0)
        self.__use_mipmap = args.get('use_mipmap', True)
        self.__sph_blend_factor = args.get('sph_blend_factor', 1.0)
        self.__spa_blend_factor = args.get('spa_blend_factor', 1.0)

        logging.info('****************************************')
        logging.info(' mmd_tools.import_pmx module')
        logging.info('----------------------------------------')
        logging.info(' Start to load model data form a pmx file')
        logging.info('            by the mmd_tools.pmx modlue.')
        logging.info('')

        start_time = time.time()

        self.__createObjects()

        if 'MESH' in types:
            self.__createMeshObject()
            self.__importVertices()
            self.__importMaterials()
            self.__importFaces()
            self.__meshObj.data.update()
            self.__assignCustomNormals()

        if 'ARMATURE' in types:
            self.__importBones()
            if args.get('rename_LR_bones', False):
                self.__renameLRBones()
            self.__rig.applyAdditionalTransformConstraints()

        if 'PHYSICS' in types:
            self.__importRigids()
            self.__importJoints()

        if 'DISPLAY' in types:
            self.__importDisplayFrames()
        else:
            self.__rig.initialDisplayFrames()

        if 'MORPHS' in types:
            self.__importGroupMorphs()
            self.__importVertexMorphs()
            self.__importBoneMorphs()
            self.__importMaterialMorphs()
            self.__importUVMorphs()

        if self.__meshObj:
            self.__addArmatureModifier(self.__meshObj, self.__armObj)

        #bpy.context.scene.gravity[2] = -9.81 * 10 * self.__scale
        root = self.__rig.rootObject()
        if 'MESH' not in types:
            root.mmd_root.show_armature = True
        else:
            root.mmd_root.show_meshes = True
        self.__targetScene.objects.active = root
        root.select = True

        logging.info(' Finished importing the model in %f seconds.', time.time() - start_time)
        logging.info('----------------------------------------')
        logging.info(' mmd_tools.import_pmx module')
        logging.info('****************************************')
