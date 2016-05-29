# more_imitating branch of mmd_tools

This is a fork version of mmd_tools.
This branch implemented more accurate MMD default shader but causes massive slowdown.

これはmmd_toolsの派生品です。
このブランチは、より正確なMMD標準シェーダーを実装していますが、大きな速度低下を起こしています。

## System Requirements / 動作環境

I tested on Blender 2.77 but it should work on other enviroments.

Blender 2.77でテストしましたが、他の環境でも動くはずです。

## Technical Notes for more_imitating branch
### Units
- 1BU (Blender Unit) = 1 MMD Unit = 8cm
- 1 blender grid = 1 mikucell = 40cm

### Axis
- Blender: right-handed Z-up
- MMD: left-handed Y-up

### Camera
This branch introduces non-Blender and more MMD-like camera operations.
This is because mmd_tools edge shader depends on Camera distance.

If you don't care edge shaders, you can switch back to normal Blender operations:
1. press [N]
2. uncheck "Lock Camera To View" option

### Resolution
- MMD: 512x288
I know it's dated but anyway I kept it for now.

### Lamp Location
- MMD: X, Y, Z = (from -1 to 1, from -1 to 1, from -1 to 1)

### Ground Shadow
Ground Shadow does not work in realtime but works in offline rendering.
for the Ground Shadow, This branch adds a Shadow Catcher object.

### Shader
MMD default shader basically uses the following forma (not accurate).
- color: (ambient + phong + flat diffuse) * tex * (binarized) ambient lambert
- alpha: alpha * tex alpha

This branch currently supported **all** MMD material parameters. The following is a list of the current status.
<dl>
  <dt>almost compatible in the realtime and offline rendering:</dt>
  <dd>diffuse, alpha, specular, shininess (hardness), ambient,
    texture, sphere texture, sub texture, shared toon texture,
    custom toon texture, double sided, edge color, edge alpha</dd>
  <dt>almost compatible in the offline rendering:</dt>
  <dd>self shadow, self shadow map, ground shadow</dd>
  <dt>somewhat compatible in the realtime and offline rendering:</dt>
  <dd>edge size</dd>
</dl>

Note: the self shadow uses ray shadow and the ground shadow uses white-colord buffer shadow.
 This is because of Blender's limitations but it causes some problems.
 e.g. (non-MMD) mirror material does not reflect materials without "self shadow".

 In blender, buffer shadows are only usable in Spot Lamps.
 so the Spot Lamp is placed with near-directional lamp parameters.
 the shadow catcher actually recieves shadow alpha and
 converts the alpha to a shadow color and alpha.
 the shadow catcher ignores Ray Shadows, using a Light Group.

#### non-MMD shaders
You can use non-MMD shaders with hacks.

##### Custom specular
1. change Render Engine to Blender Render
2. add new material slot
3. append *.spw material to empty slot
2. change specular model (e.g. from Phong to Toon)

##### Custom toon/diffuse
1. change Render Engine to Blender Render
2. add new material slot
3. append "mmd_tools Node Base" or "mmd_tools Node Base NoShadow" material to empty slot
4. change diffuse model or enable (fake) SSS (e.g. rgb: [1.0, 1.0, 1.0], rgb radius: [0.125, 0.125, 0.125])

If you want to use more smoothed toon, there are two options.
* just use the (fake) SSS. it uses blur and it makes things smooth.
* or transfer custom normals from created smoothed model to the model.

### Theme
This is still in-development and not good for normal use.
If you want to use it, just install presets/interface_theme/*.xml from blender's theme installing dialog.

## License
&copy; 2012-2016 sugiany, et al.
Distributed under the MIT License.

## original document
[README_ORIG.md](README_ORIG.md)
