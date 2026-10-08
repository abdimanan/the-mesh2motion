import { type Bone, type Object3D, type Quaternion, type Vector3 } from 'three'

interface LiftedBone {
  bone: Bone
  original_parent: Object3D
  original_position: Vector3
  original_quaternion: Quaternion
  original_scale: Vector3
}

/**
 * Moves bones out from under meshes right before an FBX export.
 *
 * Meshes rigged inside Mesh2Motion keep their root bone as a child of the skinned mesh
 * (StepWeightSkin adds bones[0] to the mesh). glTF has no problem with that, but in FBX it
 * means a LimbNode hangs off a Mesh model. Blender's FBX importer cannot build an armature
 * there and silently drops the mesh and every bone, leaving only the Null empties above
 * them. Re-parenting the root bone next to the mesh gives the layout Mixamo and Blender
 * expect, and Blender builds a normal Armature + Mesh pair.
 */
export class FbxBoneHierarchyService {
  /**
   * Re-parents every bone whose parent is a mesh onto that mesh's parent, keeping its world
   * transform, so the skin still lines up.
   *
   * @param export_root the scene handed to the FBX exporter
   * @returns a function that puts the bones back exactly where they were
   */
  public static lift_bones_out_of_meshes (export_root: Object3D): () => void {
    const bones_under_meshes: Bone[] = []

    export_root.traverse((object: Object3D) => {
      const parent = object.parent as (Object3D & { isMesh?: boolean }) | null
      if ((object as Bone).isBone === true && parent?.isMesh === true && parent.parent !== null) {
        bones_under_meshes.push(object as Bone)
      }
    })

    export_root.updateMatrixWorld(true)

    const lifted_bones: LiftedBone[] = bones_under_meshes.map((bone) => {
      const lifted: LiftedBone = {
        bone,
        original_parent: bone.parent as Object3D,
        original_position: bone.position.clone(),
        original_quaternion: bone.quaternion.clone(),
        original_scale: bone.scale.clone()
      }

      // attach() keeps the world transform while changing the parent
      const mesh = bone.parent as Object3D
      mesh.parent?.attach(bone)
      return lifted
    })

    return () => {
      lifted_bones.forEach((lifted) => {
        lifted.original_parent.add(lifted.bone)
        lifted.bone.position.copy(lifted.original_position)
        lifted.bone.quaternion.copy(lifted.original_quaternion)
        lifted.bone.scale.copy(lifted.original_scale)
        lifted.bone.updateMatrixWorld(true)
      })
    }
  }
}
