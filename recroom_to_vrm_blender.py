import argparse
import addon_utils
import importlib
import os
import re
import shutil
import sys
from math import pi
from pathlib import Path

import bpy
from mathutils import Matrix, Vector
from mathutils.kdtree import KDTree


REQUIRED_VRM_BONES = [
    "hips",
    "spine",
    "chest",
    "neck",
    "head",
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
]


def parse_args() -> argparse.Namespace:
    argv = sys.argv
    if "--" in argv:
        argv = argv[argv.index("--") + 1 :]
    else:
        argv = []
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--keep-blend", action="store_true")
    parser.add_argument("--skip-vrm", action="store_true")
    parser.add_argument("--vrm-addon-source")
    return parser.parse_args(argv)


def deselect_all() -> None:
    bpy.ops.object.select_all(action="DESELECT")


def active_object(obj: bpy.types.Object) -> None:
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)


def object_bounds_world(obj: bpy.types.Object) -> tuple[Vector, Vector]:
    if obj.type == "MESH" and obj.data.vertices:
        corners = [obj.matrix_world @ vertex.co for vertex in obj.data.vertices]
    else:
        corners = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
    min_corner = Vector(
        (min(v.x for v in corners), min(v.y for v in corners), min(v.z for v in corners))
    )
    max_corner = Vector(
        (max(v.x for v in corners), max(v.y for v in corners), max(v.z for v in corners))
    )
    return min_corner, max_corner


def bounds_center(bounds: tuple[Vector, Vector]) -> Vector:
    return (bounds[0] + bounds[1]) * 0.5


def bounds_size(bounds: tuple[Vector, Vector]) -> Vector:
    return bounds[1] - bounds[0]


def bounds_distance(a: tuple[Vector, Vector], b: tuple[Vector, Vector]) -> float:
    dx = max(a[0].x - b[1].x, b[0].x - a[1].x, 0.0)
    dy = max(a[0].y - b[1].y, b[0].y - a[1].y, 0.0)
    dz = max(a[0].z - b[1].z, b[0].z - a[1].z, 0.0)
    return Vector((dx, dy, dz)).length


def combined_bounds(objects: list[bpy.types.Object]) -> tuple[Vector, Vector]:
    mins = []
    maxs = []
    for obj in objects:
        mn, mx = object_bounds_world(obj)
        mins.append(mn)
        maxs.append(mx)
    return (
        Vector((min(v.x for v in mins), min(v.y for v in mins), min(v.z for v in mins))),
        Vector((max(v.x for v in maxs), max(v.y for v in maxs), max(v.z for v in maxs))),
    )


def rotate_mesh_geometry_around_z(
    objects: list[bpy.types.Object], angle: float, center: Vector
) -> None:
    transform = (
        Matrix.Translation(center)
        @ Matrix.Rotation(angle, 4, "Z")
        @ Matrix.Translation(-center)
    )
    for obj in objects:
        if obj.type != "MESH":
            continue
        inverse_world = obj.matrix_world.inverted()
        for vertex in obj.data.vertices:
            vertex.co = inverse_world @ (transform @ (obj.matrix_world @ vertex.co))
        obj.data.update()


def material_names(obj: bpy.types.Object) -> list[str]:
    if obj.type != "MESH":
        return []
    if obj.data.polygons:
        material_indices = {polygon.material_index for polygon in obj.data.polygons}
        used_materials = [
            obj.material_slots[index].material.name
            for index in sorted(material_indices)
            if index < len(obj.material_slots) and obj.material_slots[index].material
        ]
        if used_materials:
            return used_materials
    return [slot.material.name for slot in obj.material_slots if slot.material]


def is_head_attached_material_name(name: str) -> bool:
    lowered = name.lower()
    keywords = [
        "avatarface",
        "face",
        "hair",
        "hat",
        "beret",
        "glasses",
        "aviator",
        "eye",
        "eyebrow",
        "beard",
        "mustache",
        "moustache",
        "mouth",
        "teeth",
        "tongue",
        "lip",
    ]
    return any(keyword in lowered for keyword in keywords)


def is_head_attached_object(obj: bpy.types.Object) -> bool:
    return any(is_head_attached_material_name(name) for name in material_names(obj))


def is_strict_head_material_name(name: str) -> bool:
    lowered = name.lower()
    keywords = [
        "avatarface",
        "face",
        "hair",
        "hat",
        "headscarf",
        "glasses",
        "aviator",
        "eye",
        "eyebrow",
        "beard",
        "mustache",
        "moustache",
        "mouth",
        "teeth",
        "tongue",
        "lip",
    ]
    return any(keyword in lowered for keyword in keywords)


def is_strict_head_object(obj: bpy.types.Object) -> bool:
    return any(is_strict_head_material_name(name) for name in material_names(obj))


def is_body_attached_material_name(name: str) -> bool:
    lowered = name.lower()
    keywords = [
        "shoulder",
        "belt",
        "cape",
        "scarf",
        "neck",
        "shirt",
        "skirt",
        "jacket",
        "coat",
        "collar",
        "torso",
    ]
    return any(keyword in lowered for keyword in keywords)


def is_body_attached_object(obj: bpy.types.Object) -> bool:
    names = [obj.name] + material_names(obj)
    return any(is_body_attached_material_name(name) for name in names)


def is_hand_attached_material_name(name: str) -> bool:
    lowered = name.lower()
    keywords = [
        "hand",
        "wrist",
        "glove",
        "bracelet",
        "watch",
        "cuff",
    ]
    return any(keyword in lowered for keyword in keywords)


def is_hand_attached_object(obj: bpy.types.Object) -> bool:
    names = [obj.name] + material_names(obj)
    return any(is_hand_attached_material_name(name) for name in names)


def rig_reference_meshes(meshes: list[bpy.types.Object]) -> list[bpy.types.Object]:
    try:
        return [identify_skin_object(meshes)]
    except RuntimeError:
        return meshes


def bounds_axis_distance(
    value: float, minimum: float, maximum: float
) -> float:
    if minimum <= value <= maximum:
        return 0.0
    return min(abs(value - minimum), abs(value - maximum))


def object_vertices_world(obj: bpy.types.Object) -> list[Vector]:
    if obj.type != "MESH":
        return []
    return [obj.matrix_world @ vertex.co for vertex in obj.data.vertices]


def cleanup_scene() -> None:
    ensure_object_mode()
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    for datablock in (
        bpy.data.meshes,
        bpy.data.materials,
        bpy.data.images,
        bpy.data.armatures,
        bpy.data.cameras,
        bpy.data.lights,
    ):
        for item in list(datablock):
            if not item.users:
                datablock.remove(item)


def remove_unexported_scene_objects(
    armature: bpy.types.Object, exported_meshes: list[bpy.types.Object]
) -> None:
    keep = {armature, *exported_meshes}
    for obj in list(bpy.data.objects):
        if obj not in keep:
            bpy.data.objects.remove(obj, do_unlink=True)


def find_vrm_module_names() -> list[str]:
    return sorted(
        {
            module.__name__
            for module in addon_utils.modules()
            if "vrm" in module.__name__.lower()
        }
    )


def find_vrm_modules() -> list[object]:
    return [module for module in addon_utils.modules() if "vrm" in module.__name__.lower()]


def current_blender_version() -> tuple[int, int, int]:
    return tuple(int(v) for v in bpy.app.version[:3])


def read_source_compatible_version_range(
    source: Path,
) -> tuple[tuple[int, int, int] | None, tuple[int, int, int] | None]:
    manifest_path = source / "blender_manifest.toml"
    if not manifest_path.is_file():
        return None, None
    text = manifest_path.read_text(encoding="utf-8")

    def parse_version(key: str) -> tuple[int, int, int] | None:
        match = re.search(rf'^{key}\s*=\s*"(\d+)\.(\d+)\.(\d+)"\s*$', text, re.MULTILINE)
        if not match:
            return None
        return tuple(int(group) for group in match.groups())

    return parse_version("blender_version_min"), parse_version("blender_version_max")


def source_is_compatible_with_current_blender(source: Path) -> bool:
    minimum, maximum = read_source_compatible_version_range(source)
    version = current_blender_version()
    if minimum and version < minimum:
        return False
    if maximum and version >= maximum:
        return False
    return True


def module_is_compatible_with_current_blender(module: object) -> bool:
    module_file = getattr(module, "__file__", None)
    if not module_file:
        return True
    return source_is_compatible_with_current_blender(Path(module_file).parent)


def module_priority(module_name: str) -> tuple[int, str]:
    lowered = module_name.lower()
    if lowered == "bl_ext.user_default.vrm":
        return (0, lowered)
    if lowered.startswith("bl_ext."):
        return (1, lowered)
    if lowered.startswith("io_scene_vrm"):
        return (2, lowered)
    if "vrm_addon_for_blender" in lowered:
        return (3, lowered)
    return (4, lowered)


def enable_addon(module_name: str) -> bool:
    _, loaded_enabled = addon_utils.check(module_name)
    if loaded_enabled:
        return True
    try:
        addon_utils.enable(module_name, default_set=True, persistent=True)
    except Exception as exc:
        print(f"Failed to enable addon {module_name}: {exc}")
        return False
    try:
        bpy.ops.wm.save_userpref()
    except Exception as exc:
        print(f"Addon {module_name} enabled, but preferences could not be saved: {exc}")
    _, enabled = addon_utils.check(module_name)
    return enabled


def install_addon_from_source(source: Path) -> bool:
    user_addon_dir = Path(bpy.utils.user_resource("SCRIPTS", path="addons", create=True))
    if source.is_file() and source.suffix.lower() == ".zip":
        try:
            bpy.ops.preferences.addon_install(filepath=str(source), overwrite=True)
            addon_utils.modules_refresh()
            try:
                bpy.ops.wm.save_userpref()
            except Exception as exc:
                print(f"Addon installed from zip, but preferences could not be saved: {exc}")
            return True
        except Exception as exc:
            print(f"Failed to install addon zip {source}: {exc}")
            return False

    if source.is_dir():
        if (source / "io_scene_vrm").is_dir():
            source = source / "io_scene_vrm"
        sanitized_name = source.name.replace("-", "_").replace(" ", "_")
        target = user_addon_dir / sanitized_name
        legacy_target = user_addon_dir / source.name
        try:
            if legacy_target.exists() and legacy_target != target:
                shutil.rmtree(legacy_target)
            if target.exists():
                shutil.rmtree(target)
            shutil.copytree(source, target)
            user_addon_dir_text = str(user_addon_dir)
            if user_addon_dir_text not in sys.path:
                sys.path.insert(0, user_addon_dir_text)
            importlib.invalidate_caches()
            addon_utils.modules_refresh()
            try:
                bpy.ops.wm.save_userpref()
            except Exception as exc:
                print(f"Addon copied to {target}, but preferences could not be saved: {exc}")
            return True
        except Exception as exc:
            print(f"Failed to copy addon directory {source} to {target}: {exc}")
            return False

    print(f"Unsupported addon source: {source}")
    return False


def bundled_data_dir() -> Path:
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        return Path(meipass)
    return Path(__file__).resolve().parent


def find_candidate_vrm_addon_sources(explicit_source: str | None) -> list[Path]:
    candidates: list[Path] = []
    if explicit_source:
        candidates.append(Path(explicit_source))

    bundled_root = bundled_data_dir()
    candidates.extend(
        [
            bundled_root / "vendor" / "VRM-Addon-for-Blender" / "src" / "io_scene_vrm",
            bundled_root / "vendor" / "VRM-Addon-for-Blender" / "src",
            bundled_root / "io_scene_vrm",
        ]
    )

    blender_root = Path.home() / "AppData" / "Roaming" / "Blender Foundation" / "Blender"
    if blender_root.exists():
        for version_dir in sorted(blender_root.iterdir()):
            addon_dir = version_dir / "scripts" / "addons"
            if not addon_dir.is_dir():
                continue
            for child in addon_dir.iterdir():
                if child.name in {
                    "VRM_Addon_for_Blender-release",
                    "VRM_Addon_for_Blender_release",
                }:
                    candidates.append(child)
                elif child.suffix.lower() == ".zip" and "vrm" in child.name.lower():
                    candidates.append(child)

            extension_dir = version_dir / "extensions"
            if extension_dir.is_dir():
                for child in extension_dir.rglob("*"):
                    if child.is_dir() and child.name.lower() in {"vrm", "io_scene_vrm"}:
                        candidates.append(child)
                    elif child.is_file() and child.suffix.lower() == ".zip" and "vrm" in child.name.lower():
                        candidates.append(child)

    downloads_dir = Path.home() / "Downloads"
    if downloads_dir.exists():
        for child in downloads_dir.rglob("*"):
            if child.name in {
                "VRM_Addon_for_Blender-release",
                "VRM_Addon_for_Blender_release",
            }:
                candidates.append(child)
            elif child.suffix.lower() == ".zip" and "vrm_addon_for_blender" in child.name.lower():
                candidates.append(child)

    unique: list[Path] = []
    seen: set[str] = set()
    for path in candidates:
        key = os.path.normcase(str(path.resolve(strict=False)))
        if key in seen:
            continue
        seen.add(key)
        unique.append(path)
    return unique


def ensure_required_addons(vrm_addon_source: str | None) -> str | None:
    if not enable_addon("rigify"):
        print("Rigify could not be enabled automatically.")

    vrm_modules = sorted(find_vrm_modules(), key=lambda module: module_priority(module.__name__))
    for module in vrm_modules:
        module_name = module.__name__
        if not module_is_compatible_with_current_blender(module):
            print(
                f"Skipping incompatible installed VRM addon module {module_name} "
                f"for Blender {'.'.join(map(str, current_blender_version()))}."
            )
            continue
        if enable_addon(module_name):
            return module_name

    for source in find_candidate_vrm_addon_sources(vrm_addon_source):
        if source.is_dir() and not source_is_compatible_with_current_blender(source):
            minimum, maximum = read_source_compatible_version_range(source)
            print(
                "Skipping incompatible VRM addon source "
                f"{source} for Blender {'.'.join(map(str, current_blender_version()))}. "
                f"Supported range: {minimum} - {maximum}"
            )
            continue
        print(f"Trying to install VRM addon from: {source}")
        if not install_addon_from_source(source):
            continue
        vrm_modules = sorted(
            find_vrm_modules(), key=lambda module: module_priority(module.__name__)
        )
        for module in vrm_modules:
            module_name = module.__name__
            if not module_is_compatible_with_current_blender(module):
                continue
            if enable_addon(module_name):
                return module_name

    return None


def import_glb(path: Path) -> list[bpy.types.Object]:
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(path))
    return [obj for obj in bpy.data.objects if obj not in before]


def separate_loose_parts(obj: bpy.types.Object) -> list[bpy.types.Object]:
    deselect_all()
    active_object(obj)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.separate(type="LOOSE")
    bpy.ops.object.mode_set(mode="OBJECT")
    return [o for o in bpy.context.selected_objects if o.type == "MESH"]


def ensure_object_mode() -> None:
    if bpy.context.object and bpy.context.object.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")


def identify_skin_object(meshes: list[bpy.types.Object]) -> bpy.types.Object:
    for obj in meshes:
        names = material_names(obj)
        if any("Skin_Mat" in name for name in names):
            return obj
    raise RuntimeError("Could not find the Rec Room skin mesh.")


def select_rig_body_parts(
    head_parts: list[bpy.types.Object],
    body_parts: list[bpy.types.Object],
    all_bounds: tuple[Vector, Vector],
) -> list[bpy.types.Object]:
    if not head_parts or not body_parts:
        return body_parts

    head_bounds = combined_bounds(head_parts)
    head_center = bounds_center(head_bounds)
    full_size = bounds_size(all_bounds)
    max_x_distance = max(full_size.x * 0.12, 0.08)
    max_y_distance = max(full_size.y * 0.18, 0.08)
    torso_floor_z = all_bounds[0].z + full_size.z * 0.20

    under_head: list[bpy.types.Object] = []
    for obj in body_parts:
        bounds = object_bounds_world(obj)
        if bounds[1].z < torso_floor_z:
            continue
        if bounds[0].z > head_bounds[0].z:
            continue
        x_distance = bounds_axis_distance(head_center.x, bounds[0].x, bounds[1].x)
        y_distance = bounds_axis_distance(head_center.y, bounds[0].y, bounds[1].y)
        if x_distance <= max_x_distance and y_distance <= max_y_distance:
            under_head.append(obj)

    if under_head:
        return under_head

    def xy_distance_to_head(obj: bpy.types.Object) -> float:
        bounds = object_bounds_world(obj)
        x_distance = bounds_axis_distance(head_center.x, bounds[0].x, bounds[1].x)
        y_distance = bounds_axis_distance(head_center.y, bounds[0].y, bounds[1].y)
        return (x_distance * x_distance + y_distance * y_distance) ** 0.5

    nearest = min(body_parts, key=xy_distance_to_head)
    nearest_distance = xy_distance_to_head(nearest)
    return [
        obj
        for obj in body_parts
        if xy_distance_to_head(obj) <= nearest_distance + max(full_size.x * 0.04, 0.03)
    ]


def classify_parts(
    original_meshes: list[bpy.types.Object],
) -> dict[str, list[bpy.types.Object]]:
    meshes = [obj for obj in original_meshes if obj.type == "MESH"]
    skin_obj = identify_skin_object(meshes)
    separated = separate_loose_parts(skin_obj)

    head_attached_sources = [
        obj
        for obj in meshes
        if obj != skin_obj and is_head_attached_object(obj)
    ]
    head_attached_objects: list[bpy.types.Object] = []
    for obj in head_attached_sources:
        head_attached_objects.extend(separate_loose_parts(obj))
    face_reference_objects = [
        obj
        for obj in head_attached_objects
        if any(
            "AvatarFace" in name or "Face" in name
            for name in material_names(obj)
        )
    ]
    face_reference_bounds = (
        combined_bounds(face_reference_objects) if face_reference_objects else None
    )

    hand_attached_sources = [
        obj
        for obj in meshes
        if obj != skin_obj
        and obj not in head_attached_sources
        and obj not in head_attached_objects
        and is_hand_attached_object(obj)
    ]
    hand_attached_objects: list[bpy.types.Object] = []
    for obj in hand_attached_sources:
        hand_attached_objects.extend(separate_loose_parts(obj))

    other_objects = [
        obj
        for obj in meshes
        if obj not in separated
        and obj not in head_attached_sources
        and obj not in head_attached_objects
        and obj not in hand_attached_sources
        and obj not in hand_attached_objects
    ]
    all_meshes = separated + head_attached_objects + hand_attached_objects + other_objects
    all_bounds = combined_bounds(all_meshes)
    full_size = bounds_size(all_bounds)
    hand_x_threshold = max(full_size.x * 0.32, 0.15)
    head_z_threshold = all_bounds[0].z + full_size.z * 0.62
    skin_head_candidates: list[tuple[bpy.types.Object, tuple[Vector, Vector]]] = []
    for obj in separated:
        bounds = object_bounds_world(obj)
        center = bounds_center(bounds)
        if (
            any("Skin_Mat" in name for name in material_names(obj))
            and abs(center.x) < hand_x_threshold
            and center.z >= head_z_threshold
        ):
            skin_head_candidates.append((obj, bounds))

    skin_shoulder_head_cutoff_z: float | None = None
    sorted_skin_head_candidates = sorted(
        skin_head_candidates, key=lambda item: item[1][0].z
    )
    largest_gap = 0.0
    for lower, upper in zip(
        sorted_skin_head_candidates, sorted_skin_head_candidates[1:]
    ):
        gap = upper[1][0].z - lower[1][1].z
        if gap > largest_gap:
            largest_gap = gap
            skin_shoulder_head_cutoff_z = lower[1][1].z + gap * 0.5
    if largest_gap < max(full_size.z * 0.025, 0.025):
        skin_shoulder_head_cutoff_z = None
    face_neighbor_distance = max(full_size.x * 0.08, 0.035)

    head_parts: list[bpy.types.Object] = []
    left_hand_parts: list[bpy.types.Object] = []
    right_hand_parts: list[bpy.types.Object] = []
    body_parts: list[bpy.types.Object] = []
    separated_info: list[tuple[bpy.types.Object, Vector]] = []

    for obj in separated:
        bounds = object_bounds_world(obj)
        center = bounds_center(bounds)
        separated_info.append((obj, center))
        if center.x <= -hand_x_threshold:
            left_hand_parts.append(obj)
            continue
        if center.x >= hand_x_threshold:
            right_hand_parts.append(obj)
            continue
        if center.z >= head_z_threshold:
            is_skin_part = any("Skin_Mat" in name for name in material_names(obj))
            if is_body_attached_object(obj) and not is_strict_head_object(obj):
                body_parts.append(obj)
                continue
            if (
                is_skin_part
                and face_reference_bounds is not None
                and bounds_distance(bounds, face_reference_bounds) <= face_neighbor_distance
                and bounds[1].z >= face_reference_bounds[0].z - max(full_size.z * 0.02, 0.02)
            ):
                head_parts.append(obj)
                continue
            if (
                is_skin_part
                and face_reference_bounds is not None
                and bounds[0].z >= face_reference_bounds[0].z + max(full_size.z * 0.03, 0.03)
            ):
                head_parts.append(obj)
                continue
            if (
                is_skin_part
                and face_reference_bounds is not None
                and bounds_distance(bounds, face_reference_bounds) <= face_neighbor_distance
                and (
                    skin_shoulder_head_cutoff_z is None
                    or center.z >= skin_shoulder_head_cutoff_z
                )
            ):
                head_parts.append(obj)
                continue
            if (
                is_skin_part
                and skin_shoulder_head_cutoff_z is not None
                and bounds[1].z < skin_shoulder_head_cutoff_z
            ):
                body_parts.append(obj)
                continue
            head_parts.append(obj)
            continue
        body_parts.append(obj)

    for obj in head_attached_objects:
        center = bounds_center(object_bounds_world(obj))
        if is_body_attached_object(obj) and not is_strict_head_object(obj):
            body_parts.append(obj)
        elif is_strict_head_object(obj) or center.z >= head_z_threshold:
            head_parts.append(obj)
        elif is_body_attached_object(obj):
            body_parts.append(obj)
        else:
            body_parts.append(obj)

    for obj in other_objects:
        center = bounds_center(object_bounds_world(obj))
        if center.z >= head_z_threshold and not is_body_attached_object(obj):
            head_parts.append(obj)
        else:
            body_parts.append(obj)

    def move_from_body_to_hand(
        obj: bpy.types.Object, hand_parts: list[bpy.types.Object]
    ) -> None:
        if obj in head_parts or obj in hand_parts:
            return
        if obj in body_parts:
            body_parts.remove(obj)
        hand_parts.append(obj)

    def fill_missing_hand_from_side(
        hand_parts: list[bpy.types.Object], side: str
    ) -> int:
        if hand_parts:
            return 0
        fallback_threshold = max(full_size.x * 0.08, 0.03)
        edge_band = max(full_size.x * 0.08, 0.06)
        if side == "left":
            candidates = [
                (center.x, obj)
                for obj, center in separated_info
                if obj not in head_parts
                and obj not in right_hand_parts
                and center.z < head_z_threshold
                and center.x < 0
            ]
            if candidates:
                edge_x = min(center_x for center_x, _ in candidates)
                selected = [
                    obj
                    for center_x, obj in candidates
                    if center_x <= edge_x + edge_band
                    and abs(center_x) >= fallback_threshold
                ]
            else:
                selected = []
        else:
            candidates = [
                (center.x, obj)
                for obj, center in separated_info
                if obj not in head_parts
                and obj not in left_hand_parts
                and center.z < head_z_threshold
                and center.x > 0
            ]
            if candidates:
                edge_x = max(center_x for center_x, _ in candidates)
                selected = [
                    obj
                    for center_x, obj in candidates
                    if center_x >= edge_x - edge_band
                    and abs(center_x) >= fallback_threshold
                ]
            else:
                selected = []

        for obj in selected:
            move_from_body_to_hand(obj, hand_parts)
        return len(selected)

    def move_adjacent_body_parts_to_hand(
        hand_parts: list[bpy.types.Object],
        opposite_hand_parts: list[bpy.types.Object],
        side: str,
    ) -> int:
        if not hand_parts:
            return 0
        hand_bounds = combined_bounds(hand_parts)
        hand_center = bounds_center(hand_bounds)
        neighbor_distance = max(full_size.x * 0.035, 0.025)
        height_margin = max(full_size.z * 0.08, 0.05)
        moved = 0
        for obj in list(body_parts):
            if obj in head_parts or obj in opposite_hand_parts:
                continue
            bounds = object_bounds_world(obj)
            center = bounds_center(bounds)
            if side == "left" and center.x <= hand_center.x:
                continue
            if side == "right" and center.x >= hand_center.x:
                continue
            if bounds[1].z < hand_bounds[0].z - height_margin:
                continue
            if bounds[0].z > hand_bounds[1].z + height_margin:
                continue
            if bounds_distance(bounds, hand_bounds) > neighbor_distance:
                continue
            move_from_body_to_hand(obj, hand_parts)
            moved += 1
        return moved

    def move_vertex_adjacent_parts_to_head() -> int:
        if not head_parts:
            return 0

        head_vertices: list[Vector] = []
        for obj in head_parts:
            head_vertices.extend(object_vertices_world(obj))
        if not head_vertices:
            return 0

        tree = KDTree(len(head_vertices))
        for index, vertex in enumerate(head_vertices):
            tree.insert(vertex, index)
        tree.balance()

        head_bounds = combined_bounds(head_parts)
        head_floor = head_bounds[0].z
        adjacency_distance = max(full_size.z * 0.012, 0.012)
        head_lower_margin = max(full_size.z * 0.10, 0.06)
        moved = 0

        for obj in list(body_parts):
            if is_body_attached_object(obj) and not is_strict_head_object(obj):
                continue
            if is_hand_attached_object(obj):
                continue
            bounds = object_bounds_world(obj)
            if bounds[1].z < head_floor - head_lower_margin:
                continue
            if bounds_distance(bounds, head_bounds) > adjacency_distance:
                continue
            if any(
                tree.find(vertex)[2] <= adjacency_distance
                for vertex in object_vertices_world(obj)
            ):
                body_parts.remove(obj)
                head_parts.append(obj)
                moved += 1

        return moved

    fallback_left_count = fill_missing_hand_from_side(left_hand_parts, "left")
    fallback_right_count = fill_missing_hand_from_side(right_hand_parts, "right")
    if fallback_left_count or fallback_right_count:
        print(
            "Hand detection fallback used: "
            f"left_added={fallback_left_count}, "
            f"right_added={fallback_right_count}, "
            f"left_total={len(left_hand_parts)}, "
            f"right_total={len(right_hand_parts)}"
        )

    for obj in hand_attached_objects:
        center = bounds_center(object_bounds_world(obj))
        if center.x <= 0:
            left_hand_parts.append(obj)
        else:
            right_hand_parts.append(obj)

    adjacent_left_count = move_adjacent_body_parts_to_hand(
        left_hand_parts, right_hand_parts, "left"
    )
    adjacent_right_count = move_adjacent_body_parts_to_hand(
        right_hand_parts, left_hand_parts, "right"
    )
    if adjacent_left_count or adjacent_right_count:
        print(
            "Adjacent hand mesh detection used: "
            f"left_added={adjacent_left_count}, "
            f"right_added={adjacent_right_count}, "
            f"left_total={len(left_hand_parts)}, "
            f"right_total={len(right_hand_parts)}"
        )

    adjacent_head_count = move_vertex_adjacent_parts_to_head()
    if adjacent_head_count:
        print(
            "Adjacent head mesh detection used: "
            f"head_added={adjacent_head_count}, "
            f"head_total={len(head_parts)}"
        )

    final_meshes: list[bpy.types.Object] = []
    for obj in head_parts + left_hand_parts + right_hand_parts + body_parts:
        if obj and obj.name in bpy.data.objects and obj not in final_meshes:
            final_meshes.append(obj)

    rig_body_final = select_rig_body_parts(head_parts, body_parts, all_bounds)

    return {
        "all": final_meshes,
        "head": head_parts,
        "left_hand": left_hand_parts,
        "right_hand": right_hand_parts,
        "body": body_parts,
        "rig_body": rig_body_final,
    }


def new_bone(
    armature: bpy.types.Object,
    name: str,
    head: Vector,
    tail: Vector,
    parent: bpy.types.EditBone | None = None,
) -> bpy.types.EditBone:
    bone = armature.data.edit_bones.new(name)
    bone.head = head
    bone.tail = tail
    if (bone.tail - bone.head).length < 0.005:
        bone.tail.z += 0.03
    if parent:
        bone.parent = parent
        bone.use_connect = False
    return bone


def create_armature(groups: dict[str, list[bpy.types.Object]]) -> tuple[bpy.types.Object, dict[str, str]]:
    all_bounds = combined_bounds(groups["all"])
    full_size = bounds_size(all_bounds)
    head_bounds = combined_bounds(groups["head"])
    body_bounds = combined_bounds(groups.get("rig_body") or groups["body"])
    left_hand_bounds = combined_bounds(groups["right_hand"])
    right_hand_bounds = combined_bounds(groups["left_hand"])

    center_x = (all_bounds[0].x + all_bounds[1].x) * 0.5
    depth_y = (all_bounds[0].y + all_bounds[1].y) * 0.5
    hips_z = body_bounds[0].z + full_size.z * 0.12
    spine_z = body_bounds[0].z + full_size.z * 0.28
    chest_z = body_bounds[0].z + full_size.z * 0.47
    neck_z = head_bounds[0].z + (head_bounds[1].z - head_bounds[0].z) * 0.12
    head_z = head_bounds[0].z + (head_bounds[1].z - head_bounds[0].z) * 0.5
    top_z = head_bounds[1].z

    shoulder_z = chest_z + (neck_z - chest_z) * 0.35
    shoulder_span = max(body_bounds[1].x - body_bounds[0].x, 0.18) * 0.52
    left_shoulder = Vector((min(center_x - 0.02, -0.01), depth_y, shoulder_z))
    right_shoulder = Vector((max(center_x + 0.02, 0.01), depth_y, shoulder_z))
    left_shoulder.x = max(left_shoulder.x, body_bounds[0].x - shoulder_span * 0.1)
    right_shoulder.x = min(right_shoulder.x, body_bounds[1].x + shoulder_span * 0.1)

    def hand_center(bounds: tuple[Vector, Vector]) -> Vector:
        return Vector(
            (
                (bounds[0].x + bounds[1].x) * 0.5,
                (bounds[0].y + bounds[1].y) * 0.5,
                (bounds[0].z + bounds[1].z) * 0.5,
            )
        )

    left_hand = hand_center(left_hand_bounds)
    right_hand = hand_center(right_hand_bounds)
    left_elbow = left_shoulder.lerp(left_hand, 0.55)
    right_elbow = right_shoulder.lerp(right_hand, 0.55)
    left_hand_tail = left_hand + Vector((-0.06, 0.0, 0.0))
    right_hand_tail = right_hand + Vector((0.06, 0.0, 0.0))

    deselect_all()
    bpy.ops.object.armature_add(enter_editmode=True, location=(0, 0, 0))
    armature = bpy.context.active_object
    armature.name = "RecRoomAvatarRig"
    armature.data.name = "RecRoomAvatarRigData"

    edit_bones = armature.data.edit_bones
    edit_bones.remove(edit_bones[0])

    hips = new_bone(
        armature,
        "Hips",
        Vector((center_x, depth_y, hips_z)),
        Vector((center_x, depth_y, spine_z)),
    )
    spine = new_bone(
        armature, "Spine", hips.tail.copy(), Vector((center_x, depth_y, chest_z)), hips
    )
    chest = new_bone(
        armature, "Chest", spine.tail.copy(), Vector((center_x, depth_y, neck_z)), spine
    )
    neck = new_bone(
        armature,
        "Neck",
        chest.tail.copy(),
        Vector((center_x, depth_y, head_bounds[0].z + 0.02)),
        chest,
    )
    head = new_bone(
        armature, "Head", neck.tail.copy(), Vector((center_x, depth_y, top_z)), neck
    )

    left_shoulder_bone = new_bone(
        armature, "LeftShoulder", chest.tail.copy(), left_shoulder, chest
    )
    left_upper_arm = new_bone(
        armature, "LeftUpperArm", left_shoulder, left_elbow, left_shoulder_bone
    )
    left_lower_arm = new_bone(
        armature, "LeftLowerArm", left_elbow, left_hand, left_upper_arm
    )
    left_hand_bone = new_bone(
        armature, "LeftHand", left_hand, left_hand_tail, left_lower_arm
    )

    right_shoulder_bone = new_bone(
        armature, "RightShoulder", chest.tail.copy(), right_shoulder, chest
    )
    right_upper_arm = new_bone(
        armature, "RightUpperArm", right_shoulder, right_elbow, right_shoulder_bone
    )
    right_lower_arm = new_bone(
        armature, "RightLowerArm", right_elbow, right_hand, right_upper_arm
    )
    right_hand_bone = new_bone(
        armature, "RightHand", right_hand, right_hand_tail, right_lower_arm
    )

    leg_root_z = all_bounds[0].z - 0.05
    foot_z = all_bounds[0].z - 0.14
    foot_y = depth_y + 0.04
    foot_x = max(full_size.x * 0.12, 0.05)

    left_upper_leg = new_bone(
        armature,
        "LeftUpperLeg",
        hips.head + Vector((-foot_x, 0.0, 0.0)),
        Vector((-foot_x, depth_y, leg_root_z)),
        hips,
    )
    left_lower_leg = new_bone(
        armature,
        "LeftLowerLeg",
        left_upper_leg.tail.copy(),
        Vector((-foot_x, depth_y, foot_z)),
        left_upper_leg,
    )
    new_bone(
        armature,
        "LeftFoot",
        left_lower_leg.tail.copy(),
        Vector((-foot_x, foot_y, foot_z)),
        left_lower_leg,
    )
    right_upper_leg = new_bone(
        armature,
        "RightUpperLeg",
        hips.head + Vector((foot_x, 0.0, 0.0)),
        Vector((foot_x, depth_y, leg_root_z)),
        hips,
    )
    right_lower_leg = new_bone(
        armature,
        "RightLowerLeg",
        right_upper_leg.tail.copy(),
        Vector((foot_x, depth_y, foot_z)),
        right_upper_leg,
    )
    new_bone(
        armature,
        "RightFoot",
        right_lower_leg.tail.copy(),
        Vector((foot_x, foot_y, foot_z)),
        right_lower_leg,
    )

    bpy.ops.object.mode_set(mode="OBJECT")
    armature.show_in_front = True
    return armature, {
        "hips": "Hips",
        "spine": "Spine",
        "chest": "Chest",
        "neck": "Neck",
        "head": "Head",
        "leftShoulder": "LeftShoulder",
        "leftUpperArm": "LeftUpperArm",
        "leftLowerArm": "LeftLowerArm",
        "leftHand": "LeftHand",
        "rightShoulder": "RightShoulder",
        "rightUpperArm": "RightUpperArm",
        "rightLowerArm": "RightLowerArm",
        "rightHand": "RightHand",
        "leftUpperLeg": "LeftUpperLeg",
        "leftLowerLeg": "LeftLowerLeg",
        "leftFoot": "LeftFoot",
        "rightUpperLeg": "RightUpperLeg",
        "rightLowerLeg": "RightLowerLeg",
        "rightFoot": "RightFoot",
    }


def create_vrm_addon_armature(
    groups: dict[str, list[bpy.types.Object]],
    avatar_bounds: tuple[Vector, Vector],
) -> tuple[bpy.types.Object, dict[str, str]]:
    avatar_size = bounds_size(avatar_bounds)
    humanoid_height = max(avatar_size.z, avatar_bounds[1].z, 1.0)

    if not hasattr(bpy.ops, "icyp") or not hasattr(bpy.ops.icyp, "make_basic_armature"):
        raise RuntimeError("VRM Add-on humanoid armature operator is not available.")

    deselect_all()
    result = bpy.ops.icyp.make_basic_armature(
        skip_heavy_armature_setup=False,
        wip_with_template_mesh=False,
        tall=humanoid_height,
        head_ratio=8.0,
    )
    if "FINISHED" not in result:
        raise RuntimeError("VRM Add-on failed to create a humanoid armature.")

    armature = bpy.context.active_object
    if not armature or armature.type != "ARMATURE":
        raise RuntimeError("VRM Add-on did not leave a humanoid armature active.")
    armature.name = "RecRoomAvatarRig"
    armature.data.name = "RecRoomAvatarRigData"

    addon_to_vrm_names = {
        "shoulder.L": "leftShoulder",
        "upper_arm.L": "leftUpperArm",
        "lower_arm.L": "leftLowerArm",
        "hand.L": "leftHand",
        "shoulder.R": "rightShoulder",
        "upper_arm.R": "rightUpperArm",
        "lower_arm.R": "rightLowerArm",
        "hand.R": "rightHand",
        "upper_leg.L": "leftUpperLeg",
        "lower_leg.L": "leftLowerLeg",
        "foot.L": "leftFoot",
        "upper_leg.R": "rightUpperLeg",
        "lower_leg.R": "rightLowerLeg",
        "foot.R": "rightFoot",
    }
    bpy.ops.object.mode_set(mode="OBJECT")
    for old_name, new_name in addon_to_vrm_names.items():
        bone = armature.data.bones.get(old_name)
        if bone:
            bone.name = new_name

    named_bones = {
        "hips": "hips",
        "spine": "spine",
        "chest": "chest",
        "neck": "neck",
        "head": "head",
        "leftShoulder": "leftShoulder",
        "leftUpperArm": "leftUpperArm",
        "leftLowerArm": "leftLowerArm",
        "leftHand": "leftHand",
        "rightShoulder": "rightShoulder",
        "rightUpperArm": "rightUpperArm",
        "rightLowerArm": "rightLowerArm",
        "rightHand": "rightHand",
        "leftUpperLeg": "leftUpperLeg",
        "leftLowerLeg": "leftLowerLeg",
        "leftFoot": "leftFoot",
        "rightUpperLeg": "rightUpperLeg",
        "rightLowerLeg": "rightLowerLeg",
        "rightFoot": "rightFoot",
    }

    required_names = set(named_bones.values()) | {"root"}
    bpy.ops.object.mode_set(mode="EDIT")
    edit_bones = armature.data.edit_bones
    for bone in list(edit_bones):
        if bone.name not in required_names:
            edit_bones.remove(bone)

    bpy.ops.object.mode_set(mode="OBJECT")
    armature.show_in_front = True
    return armature, named_bones


def point_to_segment_distance(point: Vector, start: Vector, end: Vector) -> float:
    segment = end - start
    length_sq = segment.length_squared
    if length_sq == 0.0:
        return (point - start).length
    t = max(0.0, min(1.0, (point - start).dot(segment) / length_sq))
    closest = start + segment * t
    return (point - closest).length


def group_center(objects: list[bpy.types.Object]) -> Vector:
    return bounds_center(combined_bounds(objects))


def mesh_average_center(obj: bpy.types.Object) -> Vector:
    center = Vector((0.0, 0.0, 0.0))
    if obj.type != "MESH" or not obj.data.vertices:
        return center
    for vertex in obj.data.vertices:
        center += obj.matrix_world @ vertex.co
    return center / len(obj.data.vertices)


def objects_average_center(objects: list[bpy.types.Object]) -> Vector:
    center = Vector((0.0, 0.0, 0.0))
    count = 0
    for obj in objects:
        if obj.type != "MESH":
            continue
        for vertex in obj.data.vertices:
            center += obj.matrix_world @ vertex.co
            count += 1
    return center / count if count else center


def translate_mesh_geometry_world(objects: list[bpy.types.Object], delta: Vector) -> None:
    for obj in objects:
        if obj.type != "MESH":
            continue
        local_delta = obj.matrix_world.inverted().to_3x3() @ delta
        for vertex in obj.data.vertices:
            vertex.co += local_delta
        obj.data.update()


def align_arm_bone_height_to_source_hands(
    groups: dict[str, list[bpy.types.Object]],
    armature: bpy.types.Object,
    named_bones: dict[str, str],
) -> None:
    hand_height = (
        objects_average_center(groups["left_hand"]).z
        + objects_average_center(groups["right_hand"]).z
    ) * 0.5

    bpy.context.view_layer.objects.active = armature
    armature.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    edit_bones = armature.data.edit_bones

    def set_chain_height(prefix: str) -> None:
        for key in [
            f"{prefix}Shoulder",
            f"{prefix}UpperArm",
            f"{prefix}LowerArm",
            f"{prefix}Hand",
        ]:
            bone = edit_bones.get(named_bones[key])
            if not bone:
                continue
            for point in [bone.head, bone.tail]:
                point.z = hand_height
            bone.use_connect = False

    set_chain_height("left")
    set_chain_height("right")
    bpy.ops.object.mode_set(mode="OBJECT")


def align_upper_body_bones_to_head_mesh(
    groups: dict[str, list[bpy.types.Object]],
    armature: bpy.types.Object,
    named_bones: dict[str, str],
) -> None:
    head_candidates = [
        obj
        for obj in groups["head"]
        if any(
            "Skin_Mat" in name or "AvatarFace" in name or "Face" in name
            for name in material_names(obj)
        )
    ]
    if not head_candidates:
        head_candidates = groups["head"]

    head_bounds = combined_bounds(head_candidates)
    hand_height = (
        objects_average_center(groups["left_hand"]).z
        + objects_average_center(groups["right_hand"]).z
    ) * 0.5
    head_base_z = head_bounds[0].z
    head_top_z = head_bounds[1].z
    if head_top_z <= head_base_z:
        return
    head_height = head_top_z - head_base_z
    head_base_z += head_height * 0.08
    head_top_z += head_height * 0.04

    bpy.context.view_layer.objects.active = armature
    armature.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    edit_bones = armature.data.edit_bones

    chest = edit_bones.get(named_bones["chest"])
    if chest:
        chest.tail.z = hand_height
        chest.use_connect = False

    neck = edit_bones.get(named_bones["neck"])
    if neck:
        neck.head.z = hand_height
        neck.tail.z = head_base_z
        neck.use_connect = False

    head = edit_bones.get(named_bones["head"])
    if head:
        head.head.z = head_base_z
        head.tail.z = head_top_z
        head.use_connect = False

    bpy.ops.object.mode_set(mode="OBJECT")


def align_hand_meshes_to_hand_bones(
    groups: dict[str, list[bpy.types.Object]],
    armature: bpy.types.Object,
    named_bones: dict[str, str],
) -> None:
    for group_key, bone_key in [
        ("left_hand", "leftHand"),
        ("right_hand", "rightHand"),
    ]:
        objects = groups[group_key]
        bone = armature.data.bones.get(named_bones[bone_key])
        if not objects or not bone:
            continue
        bone_head = armature.matrix_world @ bone.head_local
        delta = bone_head - objects_average_center(objects)
        translate_mesh_geometry_world(objects, delta)


def align_joined_hand_meshes_to_hand_bones(
    armature: bpy.types.Object, named_bones: dict[str, str]
) -> None:
    for object_name, bone_key in [
        ("MergedLeftHand", "leftHand"),
        ("MergedRightHand", "rightHand"),
    ]:
        obj = bpy.data.objects.get(object_name)
        bone = armature.data.bones.get(named_bones[bone_key])
        if not obj or not bone:
            continue
        bone_head = armature.matrix_world @ bone.head_local
        delta = bone_head - mesh_average_center(obj)
        translate_mesh_geometry_world([obj], delta)


def add_armature_modifier(obj: bpy.types.Object, armature: bpy.types.Object) -> None:
    modifier = obj.modifiers.get("Armature")
    if not modifier:
        modifier = obj.modifiers.new(name="Armature", type="ARMATURE")
    modifier.object = armature


def ensure_vertex_groups(obj: bpy.types.Object, bone_names: list[str]) -> None:
    for bone_name in bone_names:
        if bone_name not in obj.vertex_groups:
            obj.vertex_groups.new(name=bone_name)


def assign_entire_object(obj: bpy.types.Object, group_name: str) -> None:
    indices = [vertex.index for vertex in obj.data.vertices]
    if indices:
        obj.vertex_groups[group_name].add(indices, 1.0, "REPLACE")


def clear_vertex_group_weights(obj: bpy.types.Object, group_names: list[str]) -> None:
    for group_name in group_names:
        group = obj.vertex_groups.get(group_name)
        if group:
            indices = [vertex.index for vertex in obj.data.vertices]
            if indices:
                group.remove(indices)


def assign_object_exclusively_to_bone(obj: bpy.types.Object, bone_name: str) -> None:
    ensure_vertex_groups(obj, [bone_name])
    for group in list(obj.vertex_groups):
        if group.name != bone_name:
            obj.vertex_groups.remove(group)
    assign_entire_object(obj, bone_name)


def weight_body_object(obj: bpy.types.Object, armature: bpy.types.Object, named_bones: dict[str, str]) -> None:
    bone_names = [
        named_bones["hips"],
        named_bones["spine"],
        named_bones["chest"],
        named_bones["neck"],
        named_bones["head"],
    ]
    ensure_vertex_groups(obj, bone_names)

    pose_bones = armature.pose.bones
    segments = {
        bone_name: (
            armature.matrix_world @ pose_bones[bone_name].head,
            armature.matrix_world @ pose_bones[bone_name].tail,
        )
        for bone_name in bone_names
    }

    for vertex in obj.data.vertices:
        point = obj.matrix_world @ vertex.co
        scored = []
        for bone_name, (start, end) in segments.items():
            dist = point_to_segment_distance(point, start, end)
            score = 1.0 / max(dist, 0.002)
            scored.append((bone_name, score))
        scored.sort(key=lambda item: item[1], reverse=True)
        top = scored[:2]
        total = sum(score for _, score in top)
        for bone_name, score in top:
            obj.vertex_groups[bone_name].add(
                [vertex.index], score / total if total else 1.0, "REPLACE"
            )


def weight_hand_object(
    obj: bpy.types.Object,
    armature: bpy.types.Object,
    lower_arm_bone_name: str,
    hand_bone_name: str,
) -> None:
    ensure_vertex_groups(obj, [lower_arm_bone_name, hand_bone_name])
    clear_vertex_group_weights(obj, [lower_arm_bone_name, hand_bone_name])
    assign_entire_object(obj, hand_bone_name)


def bind_meshes(
    groups: dict[str, list[bpy.types.Object]],
    armature: bpy.types.Object,
    named_bones: dict[str, str],
) -> None:
    bone_names = list(named_bones.values())
    for obj in groups["all"]:
        if obj.type != "MESH":
            continue
        add_armature_modifier(obj, armature)
        ensure_vertex_groups(obj, bone_names)
        if obj in groups["head"]:
            assign_entire_object(obj, named_bones["head"])
        elif obj in groups["left_hand"]:
            weight_hand_object(
                obj,
                armature,
                named_bones["leftLowerArm"],
                named_bones["leftHand"],
            )
        elif obj in groups["right_hand"]:
            weight_hand_object(
                obj,
                armature,
                named_bones["rightLowerArm"],
                named_bones["rightHand"],
            )
        obj.parent = armature


def ensure_placeholder_material(name: str) -> bpy.types.Material:
    material = bpy.data.materials.get(name)
    if not material:
        material = bpy.data.materials.new(name)
    material.diffuse_color = (0.15, 0.45, 0.9, 0.0)
    material.use_nodes = True
    material.blend_method = "BLEND"
    material.show_transparent_back = True
    principled = next(
        (node for node in material.node_tree.nodes if node.type == "BSDF_PRINCIPLED"),
        None,
    )
    if principled:
        base_color_input = principled.inputs.get("Base Color")
        if base_color_input:
            base_color_input.default_value = (0.15, 0.45, 0.9, 0.0)
        alpha_input = principled.inputs.get("Alpha")
        if alpha_input:
            alpha_input.default_value = 0.0
    return material


def create_box_mesh_object(
    name: str, center: Vector, size: Vector, material: bpy.types.Material
) -> bpy.types.Object:
    half = size * 0.5
    vertices = [
        (center.x - half.x, center.y - half.y, center.z - half.z),
        (center.x + half.x, center.y - half.y, center.z - half.z),
        (center.x + half.x, center.y + half.y, center.z - half.z),
        (center.x - half.x, center.y + half.y, center.z - half.z),
        (center.x - half.x, center.y - half.y, center.z + half.z),
        (center.x + half.x, center.y - half.y, center.z + half.z),
        (center.x + half.x, center.y + half.y, center.z + half.z),
        (center.x - half.x, center.y + half.y, center.z + half.z),
    ]
    faces = [
        (0, 1, 2, 3),
        (4, 7, 6, 5),
        (0, 4, 5, 1),
        (1, 5, 6, 2),
        (2, 6, 7, 3),
        (3, 7, 4, 0),
    ]
    mesh = bpy.data.meshes.new(name + "Mesh")
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    mesh.materials.append(material)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    return obj


def create_placeholder_foot_boxes(
    armature: bpy.types.Object, named_bones: dict[str, str]
) -> list[bpy.types.Object]:
    material = ensure_placeholder_material("FootPlaceholder_Mat")
    created: list[bpy.types.Object] = []
    for object_name, bone_key in [
        ("LeftFootPlaceholderBox", "leftFoot"),
        ("RightFootPlaceholderBox", "rightFoot"),
    ]:
        bone_name = named_bones[bone_key]
        pose_bone = armature.pose.bones[bone_name]
        head = armature.matrix_world @ pose_bone.head
        tail = armature.matrix_world @ pose_bone.tail
        center = (head + tail) * 0.5
        box = create_box_mesh_object(
            object_name,
            center + Vector((0.0, 0.0, -0.02)),
            Vector((0.002, 0.002, 0.002)),
            material,
        )
        add_armature_modifier(box, armature)
        ensure_vertex_groups(box, [bone_name])
        assign_entire_object(box, bone_name)
        box.parent = armature
        created.append(box)
    return created


def join_mesh_objects(
    objects: list[bpy.types.Object], joined_name: str, armature: bpy.types.Object
) -> bpy.types.Object | None:
    mesh_objects = [obj for obj in objects if obj and obj.type == "MESH"]
    if not mesh_objects:
        return None
    if len(mesh_objects) == 1:
        mesh_objects[0].name = joined_name
        add_armature_modifier(mesh_objects[0], armature)
        mesh_objects[0].parent = armature
        return mesh_objects[0]
    deselect_all()
    for obj in mesh_objects:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = mesh_objects[0]
    bpy.ops.object.join()
    joined = bpy.context.view_layer.objects.active
    joined.name = joined_name[:60]
    add_armature_modifier(joined, armature)
    joined.parent = armature
    return joined


def material_signature(obj: bpy.types.Object) -> tuple[str, ...]:
    if obj.type != "MESH":
        return tuple()
    return tuple(
        slot.material.name if slot.material else "<none>" for slot in obj.material_slots
    )


def is_foot_placeholder_object(obj: bpy.types.Object) -> bool:
    if obj.type != "MESH":
        return False
    if obj.name.startswith(("LeftFootPlaceholderBox", "RightFootPlaceholderBox")):
        return True
    return any("FootPlaceholder_Mat" in name for name in material_names(obj))


def consolidate_meshes_for_cluster(
    armature: bpy.types.Object,
    groups: dict[str, list[bpy.types.Object]],
    named_bones: dict[str, str],
) -> list[bpy.types.Object]:
    ensure_object_mode()
    armature_meshes = [
        obj
        for obj in bpy.data.objects
        if obj.type == "MESH" and obj.parent == armature
    ]
    left_hand_set = {obj for obj in groups["left_hand"] if obj in armature_meshes}
    right_hand_set = {obj for obj in groups["right_hand"] if obj in armature_meshes}
    head_set = {obj for obj in groups["head"] if obj in armature_meshes}
    foot_placeholder_set = {
        obj for obj in armature_meshes if is_foot_placeholder_object(obj)
    }
    preserved = left_hand_set | right_hand_set | head_set | foot_placeholder_set
    body_meshes = [obj for obj in armature_meshes if obj not in preserved]

    joined_objects: list[bpy.types.Object] = []
    foot_joined = join_mesh_objects(
        list(foot_placeholder_set), "Merged_FootPlaceholder_Mat", armature
    )
    if foot_joined:
        joined_objects.append(foot_joined)

    head_joined = join_mesh_objects(list(head_set), "MergedHead", armature)
    if head_joined:
        joined_objects.append(head_joined)

    body_joined = join_mesh_objects(body_meshes, "MergedBody", armature)
    if body_joined:
        assign_object_exclusively_to_bone(body_joined, named_bones["hips"])
        joined_objects.append(body_joined)

    left_joined = join_mesh_objects(list(left_hand_set), "MergedLeftHand", armature)
    if left_joined:
        joined_objects.append(left_joined)

    right_joined = join_mesh_objects(list(right_hand_set), "MergedRightHand", armature)
    if right_joined:
        joined_objects.append(right_joined)

    return joined_objects


def try_setup_vrm(
    armature: bpy.types.Object,
    output_path: Path,
    vrm_module_name: str | None,
    named_bones: dict[str, str],
) -> bool:
    if not vrm_module_name:
        print("VRM addon is not available in this Blender profile. Skipping VRM export.")
        return False
    if not hasattr(bpy.ops, "vrm") or not hasattr(bpy.ops.export_scene, "vrm"):
        print("VRM operators are not available after addon enable. Skipping VRM export.")
        return False

    deselect_all()
    active_object(armature)
    try:
        ext = armature.data.vrm_addon_extension
    except Exception as exc:
        print(f"VRM extension properties are not available on the armature: {exc}")
        return False

    ext.spec_version = "1.0"

    meta = ext.vrm1.meta
    meta.vrm_name = output_path.stem
    meta.version = "0.1.0"
    meta.copyright_information = "Rec Room avatar source data"
    meta.contact_information = ""
    meta.third_party_licenses = ""
    meta.avatar_permission = "onlyAuthor"
    meta.allow_excessively_violent_usage = False
    meta.allow_excessively_sexual_usage = False
    meta.commercial_usage = "personalNonProfit"
    meta.allow_political_or_religious_usage = False
    meta.allow_antisocial_or_hate_usage = False
    meta.credit_notation = "required"
    meta.allow_redistribution = False
    meta.modification = "allowModification"
    meta.other_license_url = ""
    meta.authors.clear()
    author = meta.authors.add()
    author.value = "Codex RecRoom Converter"
    meta.references.clear()
    reference = meta.references.add()
    reference.value = "Rec Room avatar auto-converted to VRM"

    # Move the first-person reference point slightly above and in front of the
    # head, and hide torso/head meshes in first-person VR views when supported.
    ext.vrm1.look_at.offset_from_head_bone = (-0.04, 0.10, 0.0)
    first_person = ext.vrm1.first_person
    first_person.mesh_annotations.clear()
    first_person_mesh_types = {
        "MergedBody": "thirdPersonOnly",
        "MergedHead": "thirdPersonOnly",
        "MergedLeftHand": "both",
        "MergedRightHand": "both",
        "Merged_FootPlaceholder_Mat": "thirdPersonOnly",
    }
    for object_name, first_person_type in first_person_mesh_types.items():
        obj = bpy.data.objects.get(object_name)
        if not obj or obj.type != "MESH":
            continue
        annotation = first_person.mesh_annotations.add()
        annotation.node.mesh_object_name = obj.name
        annotation.type = first_person_type

    human_bones = ext.vrm1.humanoid.human_bones
    human_bones.filter_by_human_bone_hierarchy = False
    human_bones.allow_non_humanoid_rig = False
    mapping = {
        "hips": named_bones["hips"],
        "spine": named_bones["spine"],
        "chest": named_bones["chest"],
        "neck": named_bones["neck"],
        "head": named_bones["head"],
        "left_shoulder": named_bones["leftShoulder"],
        "left_upper_arm": named_bones["leftUpperArm"],
        "left_lower_arm": named_bones["leftLowerArm"],
        "left_hand": named_bones["leftHand"],
        "right_shoulder": named_bones["rightShoulder"],
        "right_upper_arm": named_bones["rightUpperArm"],
        "right_lower_arm": named_bones["rightLowerArm"],
        "right_hand": named_bones["rightHand"],
        "left_upper_leg": named_bones["leftUpperLeg"],
        "left_lower_leg": named_bones["leftLowerLeg"],
        "left_foot": named_bones["leftFoot"],
        "right_upper_leg": named_bones["rightUpperLeg"],
        "right_lower_leg": named_bones["rightLowerLeg"],
        "right_foot": named_bones["rightFoot"],
    }
    for vrm_bone_name, blender_bone_name in mapping.items():
        getattr(human_bones, vrm_bone_name).node.bone_name = blender_bone_name

    error_messages = list(human_bones.error_messages())
    if error_messages:
        print("VRM1 human bone validation warnings:")
        for message in error_messages:
            print(f"  - {message}")

    try:
        result = bpy.ops.export_scene.vrm(filepath=str(output_path))
    except Exception as exc:
        print(f"VRM export failed: {exc}")
        return False
    if "FINISHED" not in result:
        return False
    return True


def export_rigged_glb(output_path: Path) -> Path:
    rigged_glb = output_path.with_name(output_path.stem + ".rigged.glb")
    deselect_all()
    for obj in bpy.data.objects:
        if obj.type in {"ARMATURE", "MESH"}:
            obj.select_set(True)
    bpy.ops.export_scene.gltf(
        filepath=str(rigged_glb),
        export_format="GLB",
        use_selection=True,
        export_skins=True,
        export_yup=True,
    )
    return rigged_glb


def save_blend(output_path: Path) -> Path:
    blend_path = output_path.with_name(output_path.stem + ".blend")
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))
    return blend_path


def main() -> None:
    args = parse_args()
    input_path = Path(args.input)
    output_path = Path(args.output)
    vrm_module_name = ensure_required_addons(args.vrm_addon_source)

    cleanup_scene()
    imported = import_glb(input_path)
    mesh_objects = [obj for obj in imported if obj.type == "MESH"]
    if not mesh_objects:
        raise RuntimeError("The imported GLB does not contain any mesh objects.")

    import_bounds = combined_bounds(rig_reference_meshes(mesh_objects))
    rotate_mesh_geometry_around_z(mesh_objects, pi, bounds_center(import_bounds))

    groups = classify_parts(mesh_objects)
    if not groups["left_hand"] or not groups["right_hand"]:
        raise RuntimeError("Failed to detect both hand meshes from the skin object.")
    if not groups["head"]:
        raise RuntimeError("Failed to detect head mesh parts.")

    armature, named_bones = create_vrm_addon_armature(groups, import_bounds)
    align_arm_bone_height_to_source_hands(groups, armature, named_bones)
    align_upper_body_bones_to_head_mesh(groups, armature, named_bones)
    align_hand_meshes_to_hand_bones(groups, armature, named_bones)
    bind_meshes(groups, armature, named_bones)
    foot_boxes = create_placeholder_foot_boxes(armature, named_bones)
    print(
        "Classified parts: "
        f"head={len(groups['head'])}, "
        f"left_hand={len(groups['left_hand'])}, "
        f"right_hand={len(groups['right_hand'])}, "
        f"body={len(groups['body'])}"
    )
    print(f"Placeholder foot boxes: {len(foot_boxes)}")
    consolidated = consolidate_meshes_for_cluster(armature, groups, named_bones)
    align_joined_hand_meshes_to_hand_bones(armature, named_bones)
    remove_unexported_scene_objects(armature, consolidated)
    print(f"Consolidated mesh objects for export: {len(consolidated)}")

    rigged_glb = export_rigged_glb(output_path)
    print(f"Rigged GLB exported to: {rigged_glb}")

    if args.keep_blend:
        blend_path = save_blend(output_path)
        print(f"Blend file saved to: {blend_path}")

    if not args.skip_vrm:
        if try_setup_vrm(armature, output_path, vrm_module_name, named_bones):
            print(f"VRM exported to: {output_path}")
        else:
            raise RuntimeError("VRM export failed. Install or enable a Blender VRM addon and rerun.")


if __name__ == "__main__":
    main()
