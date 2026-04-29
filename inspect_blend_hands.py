import math

import bpy
from mathutils import Vector


def evaluated_center(obj: bpy.types.Object) -> Vector:
    depsgraph = bpy.context.evaluated_depsgraph_get()
    evaluated = obj.evaluated_get(depsgraph)
    mesh = evaluated.to_mesh()
    try:
        if not mesh.vertices:
            return Vector((0.0, 0.0, 0.0))
        center = Vector((0.0, 0.0, 0.0))
        for vertex in mesh.vertices:
            center += evaluated.matrix_world @ vertex.co
        return center / len(mesh.vertices)
    finally:
        evaluated.to_mesh_clear()


def print_mesh_binding(name: str) -> None:
    obj = bpy.data.objects.get(name)
    print(f"TARGET {name} exists={bool(obj)}")
    if not obj:
        return
    raw_center = Vector((0.0, 0.0, 0.0))
    for vertex in obj.data.vertices:
        raw_center += obj.matrix_world @ vertex.co
    raw_center = raw_center / len(obj.data.vertices) if obj.data.vertices else raw_center
    center = evaluated_center(obj)
    print(f"  raw_center={tuple(round(value, 4) for value in raw_center)}")
    print(f"  center={tuple(round(value, 4) for value in center)}")
    print(f"  parent={obj.parent.name if obj.parent else None}")
    modifiers = [
        (modifier.name, modifier.type, modifier.object.name if getattr(modifier, "object", None) else None)
        for modifier in obj.modifiers
    ]
    print(f"  modifiers={modifiers}")

    counts: dict[str, int] = {}
    sums: dict[str, float] = {}
    for vertex in obj.data.vertices:
        for group in vertex.groups:
            group_name = obj.vertex_groups[group.group].name
            lowered = group_name.lower()
            if "hand" in lowered or "arm" in lowered or "foot" in lowered or "leg" in lowered:
                counts[group_name] = counts.get(group_name, 0) + 1
                sums[group_name] = sums.get(group_name, 0.0) + group.weight
    print(f"  arm_hand_weight_counts={counts}")
    print(f"  arm_hand_weight_sums={{{', '.join(f'{k}: {round(v, 3)}' for k, v in sums.items())}}}")


def print_bone_position(armature: bpy.types.Object, name: str) -> None:
    bone = armature.data.bones.get(name)
    if not bone:
        print(f"BONE {name} exists=False")
        return
    head = armature.matrix_world @ bone.head_local
    tail = armature.matrix_world @ bone.tail_local
    print(
        f"BONE {name} head={tuple(round(value, 4) for value in head)} "
        f"tail={tuple(round(value, 4) for value in tail)}"
    )


def main() -> None:
    armature = bpy.data.objects.get("RecRoomAvatarRig")
    print(f"ARMATURE {armature.name if armature else None}")
    meshes = [
        obj.name
        for obj in bpy.data.objects
        if obj.type == "MESH" and ("Hand" in obj.name or obj.parent == armature)
    ]
    print(f"MESHES {meshes}")

    print_mesh_binding("MergedLeftHand")
    print_mesh_binding("MergedRightHand")
    print_mesh_binding("Merged_FootPlaceholder_Mat")
    print_mesh_binding("LeftFootPlaceholderBox")
    print_mesh_binding("RightFootPlaceholderBox")
    if armature:
        for bone_name in [
            "LeftUpperArm",
            "LeftLowerArm",
            "LeftHand",
            "RightUpperArm",
            "RightLowerArm",
            "RightHand",
            "LeftUpperLeg",
            "LeftLowerLeg",
            "LeftFoot",
            "RightUpperLeg",
            "RightLowerLeg",
            "RightFoot",
            "upper_arm.L",
            "lower_arm.L",
            "hand.L",
            "upper_arm.R",
            "lower_arm.R",
            "hand.R",
            "upper_leg.L",
            "lower_leg.L",
            "foot.L",
            "upper_leg.R",
            "lower_leg.R",
            "foot.R",
            "leftUpperArm",
            "leftLowerArm",
            "leftHand",
            "rightUpperArm",
            "rightLowerArm",
            "rightHand",
            "leftUpperLeg",
            "leftLowerLeg",
            "leftFoot",
            "rightUpperLeg",
            "rightLowerLeg",
            "rightFoot",
        ]:
            print_bone_position(armature, bone_name)

    left_hand = bpy.data.objects.get("MergedLeftHand")
    if not armature or not left_hand:
        return
    pose_bone = armature.pose.bones.get("LeftHand")
    print(f"POSE_BONE_LeftHand {bool(pose_bone)}")
    if not pose_bone:
        return

    pose_bone.rotation_mode = "XYZ"
    pose_bone.rotation_euler = (0.0, 0.0, 0.0)
    bpy.context.view_layer.update()
    before = evaluated_center(left_hand)

    pose_bone.rotation_euler = (0.0, 0.0, math.radians(45.0))
    bpy.context.view_layer.update()
    after = evaluated_center(left_hand)
    delta = after - before
    print(f"LEFT_HAND_CENTER_BEFORE {tuple(round(value, 4) for value in before)}")
    print(f"LEFT_HAND_CENTER_AFTER {tuple(round(value, 4) for value in after)}")
    print(f"LEFT_HAND_DELTA {tuple(round(value, 4) for value in delta)}")


main()
