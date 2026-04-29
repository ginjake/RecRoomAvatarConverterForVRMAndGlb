# Rec Room Avatar Converter

Convert a Rec Room avatar export GLB into a rigged GLB, and export VRM when a Blender VRM addon is available.

## What It Does

- Splits `Skin_Mat` into loose parts and extracts left and right hands
- Detects head and face parts automatically
- Builds a simple humanoid armature
- Assigns automatic weights
- Always writes a rigged `.glb`
- Writes an inspectable `.blend` by default
- Writes a `.vrm` when Blender has a working VRM exporter addon enabled

## Distribution Design

- `recroom-vrm-converter-gui` is the user-facing Windows GUI entrypoint
- `recroom-vrm-converter` remains available as an internal CLI
- `pyproject.toml` defines installable entrypoints for packaging
- `recroom_converter.example.toml` allows site-specific Blender and addon paths without code edits
- `build_exe.ps1` and `RecRoomVrmConverter.spec` build a Windows `.exe` with PyInstaller

## Requirements

- Blender 4.2 to 4.5 is recommended for VRM export with current local VRM addons
- Blender 5.1 can still produce a rigged `.glb`, but local VRM addons found so far are not compatible with 5.1
- A VRM exporter addon installed in a compatible Blender profile if you want `.vrm` output
- PyInstaller is required only when building the distributable `.exe`

## GUI Usage

After installation, launch `recroom-vrm-converter-gui`.
For a source checkout on Windows, you can double-click [launch_gui.pyw](E:\programing\RecRoomコンバーター\launch_gui.pyw).

1. Select the Rec Room `.glb`
2. Select the output `.vrm`
3. Confirm `blender.exe`
4. Optionally set a VRM addon zip or folder
5. Click `Convert`

The GUI runs Blender without showing a command prompt window.

## EXE Build

For distribution to end users, build [RecRoomVrmConverter.exe](E:\programing\RecRoomコンバーター\RecRoomVrmConverter.spec) with PyInstaller:

```powershell
python -m pip install pyinstaller
.\build_exe.ps1
```

The distributable executable will be created at:

```text
dist\RecRoomVrmConverter\RecRoomVrmConverter.exe
```

## CLI Example

```powershell
python .\convert_recroom_avatar.py `
  .\AvatarData_35391371_AvatarData_Me_20260424_203049\Avatar_3D\Avatar_ginjake.glb `
  .\out\Avatar_ginjake.vrm
```

If no compatible VRM addon is available, the converter still creates `Avatar_ginjake.rigged.glb`.

## Current Limits

- The part classifier is tuned for the current Rec Room avatar export layout.
- Lower-body bones are placeholders because the exported avatar does not contain full leg geometry.
- Weighting is intentionally simple and may need manual cleanup around shoulders and elbows.
