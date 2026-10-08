import { type Bone, DetachedBindMode, Matrix4, type Quaternion, type SkinnedMesh, type Vector3 } from 'three'

interface SavedBoneTransform {
  bone: Bone
  position: Vector3
  quaternion: Quaternion
  scale: Vector3
}

/**
 * Puts the skeleton back in its bind pose (the pose the mesh was skinned in) for an export.
 *
 * A "skeleton only" export has no skinned mesh, so the exporters have no bind matrices and
 * write each bone's current local transform as its rest pose. The preview keeps playing
 * while the download settings are open, so the rest pose ended up being whatever frame was
 * on screen instead of the T-pose.
 *
 * The bind pose is recovered from the skin itself (the bone world matrices that leave the
 * mesh undeformed) rather than from the bone's current parent. That stays correct when the
 * app scales or moves the model after binding (the retarget page scales large imports),
 * which is the case native Skeleton.pose() gets wrong.
 */
export class ExportRestPoseService {
  /**
   * @param skinned_meshes meshes whose skeletons should be posed at bind time
   * @returns a function that restores the pose the bones were in before
   */
  public static apply_bind_pose (skinned_meshes: SkinnedMesh[]): () => void {
    const saved_transforms: SavedBoneTransform[] = []
    const bind_world_by_bone = this.bind_world_matrices(skinned_meshes)

    const parent_inverse = new Matrix4()
    const local_matrix = new Matrix4()
    const posed_bones = new Set<Bone>()

    // parents have to be posed before their children, and the bone list is not ordered
    const pose_bone = (bone: Bone): void => {
      if (posed_bones.has(bone)) return
      posed_bones.add(bone)

      const parent_bone = bone.parent as Bone | null
      if (parent_bone !== null && bind_world_by_bone.has(parent_bone)) {
        pose_bone(parent_bone)
      }

      saved_transforms.push({
        bone,
        position: bone.position.clone(),
        quaternion: bone.quaternion.clone(),
        scale: bone.scale.clone()
      })

      const bind_world = bind_world_by_bone.get(bone) as Matrix4
      if (bone.parent !== null) {
        bone.parent.updateWorldMatrix(true, false)
        parent_inverse.copy(bone.parent.matrixWorld).invert()
        local_matrix.copy(parent_inverse).multiply(bind_world)
      } else {
        local_matrix.copy(bind_world)
      }

      local_matrix.decompose(bone.position, bone.quaternion, bone.scale)
      bone.updateMatrixWorld(true)
    }

    bind_world_by_bone.forEach((_bind_world, bone) => { pose_bone(bone) })

    return () => {
      saved_transforms.forEach((saved) => {
        saved.bone.position.copy(saved.position)
        saved.bone.quaternion.copy(saved.quaternion)
        saved.bone.scale.copy(saved.scale)
      })
      saved_transforms.forEach((saved) => { saved.bone.updateMatrixWorld(true) })
    }
  }

  /**
   * The world matrix each bone has when the skin is undeformed, whatever pose the bones
   * are in right now.
   */
  public static bind_world_matrices (skinned_meshes: SkinnedMesh[]): Map<Bone, Matrix4> {
    const bind_world_by_bone = new Map<Bone, Matrix4>()

    skinned_meshes.forEach((skinned_mesh) => {
      skinned_mesh.updateWorldMatrix(true, false)
      const skeleton = skinned_mesh.skeleton

      // The skin is undeformed when bindMatrixInverse * boneWorld * boneInverse * bindMatrix
      // is the identity. bindMatrixInverse follows the mesh's current world matrix in
      // attached mode (the default) and stays at bind time in detached mode. It is only
      // refreshed inside updateMatrixWorld, so it is worked out here instead of read.
      const skin_space = skinned_mesh.bindMode === DetachedBindMode
        ? skinned_mesh.bindMatrix
        : skinned_mesh.matrixWorld
      const unbind = new Matrix4().copy(skin_space).multiply(new Matrix4().copy(skinned_mesh.bindMatrix).invert())

      skeleton.bones.forEach((bone, index) => {
        // a bone shared by several meshes keeps the first bind pose we see
        if (bone === undefined || bone === null || bind_world_by_bone.has(bone)) {
          return
        }

        const bind_world = new Matrix4()
          .copy(unbind)
          .multiply(new Matrix4().copy(skeleton.boneInverses[index]).invert())

        bind_world_by_bone.set(bone, bind_world)
      })
    })

    return bind_world_by_bone
  }
}
