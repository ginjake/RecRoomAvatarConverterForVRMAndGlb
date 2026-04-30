<img width="1536" height="1024" alt="ChatGPT Image 2026年4月30日 17_01_55" src="https://github.com/user-attachments/assets/02fd4372-11f1-4a56-84b5-29c885b7c982" />

# Rec Room VRM Converter

Rec Roomのアバター書き出し `.glb` を、clusterなどで使いやすいHumanoid VRMやResoniteで扱いやすいリグ付きglbに変換するWindows向けツールです。

This is a Windows tool that converts Rec Room avatar export `.glb` files into Humanoid VRM files for platforms such as cluster.

返還前
<img width="664" height="1025" alt="image" src="https://github.com/user-attachments/assets/1b880077-2434-443c-9035-e82bd8537cad" />
<img width="641" height="1006" alt="image" src="https://github.com/user-attachments/assets/2e99b22e-6eef-4beb-9a17-1b94c88a6b9d" />


## How to Use / 使い方

RecRoomから下記の設定アバターをExportしてください。
足付きは対応していません。
<img width="1749" height="1054" alt="image" src="https://github.com/user-attachments/assets/ff569f31-e229-4bc2-a717-dcf3ebb27db0" />



1. GitHub Releasesから配布用zipをダウンロードします。
2. zipを展開します。
3. `RecRoomVrmConverter.exe` を起動します。
4. 変換元のGLBと、保存先を選びます。
5. `Convert` を押します。
<img width="887" height="641" alt="image" src="https://github.com/user-attachments/assets/c9e48e44-2929-4e0e-80be-8656c9e5c4ba" />
6. VRMとrig付きのglbとblendファイルが生成されていれば成功です

1. Download the release zip from GitHub Releases.
2. Extract the zip.
3. Run `RecRoomVrmConverter.exe`.
4. Select the input GLB and output VRM path.
5. Click `Convert`.

## Requirements / 必要なもの

- Windows
- Blender 5.1
- Rec Room avatar export `.glb`

Blender 5.1で動作確認しています。Blender欄が空の場合、このツールは標準インストール先のBlender 5.1を自動検出します。

This tool is tested with Blender 5.1. If the Blender field is empty, it tries to find Blender 5.1 in the standard install location.

VRM Addonは通常、手動指定不要です。配布版には変換に必要なVRM Addonを同梱し、変換時にBlender側で自動有効化します。

Normally, you do not need to select a VRM Addon manually. The release package includes the VRM Addon needed for conversion, and the converter enables it in Blender automatically.

## Limitations / 制限

- 足付きのRec Roomアバターには非対応です。
- This tool does not support Rec Room avatars with legs.
- Rec Roomの標準的な上半身アバター書き出しを対象にしています。
- It targets the standard upper-body Rec Room avatar export layout.
- 複雑な衣装やアクセサリでは、メッシュ分類やウェイトに追加調整が必要になる場合があります。
- Complex outfits or accessories may still require classifier or weight adjustments.

## What It Does

- Imports a Rec Room avatar `.glb`
- Separates body, head, face, hair, hat, beard, hands, and accessories
- Merges head-connected parts into the head mesh and weights them to `head`
- Merges body and clothes into the body mesh and weights them to `hips`
- Creates a VRM humanoid rig using the Blender VRM Addon
- Exports `.vrm`
- Also writes an inspectable `.blend` next to the output

## Developer Build / 開発者向けビルド

PythonとPyInstallerが必要なのは、配布用exeを作る開発者だけです。

Only developers who build the distributable exe need Python and PyInstaller.

The release build expects a compatible VRM Addon source at:

```text
vendor\VRM-Addon-for-Blender\src\io_scene_vrm
```

`vendor/` is ignored by Git because it is third-party code. Before publishing a release that includes the addon, check the addon's license and include the required license files or notices in the release package.

```powershell
python -m pip install pyinstaller
.\build_exe.ps1
```

The distributable files are created in:

```text
dist\RecRoomVrmConverter\
```

For GitHub Releases, package the contents of `dist\RecRoomVrmConverter\` as a zip.

## Repository Notes

Generated files and redistributable packages are intentionally ignored by Git:

- `build/`
- `dist/`
- `out/`
- `*.blend`
- `*.glb`
- `*.vrm`
- release archives such as `*.zip` and `*.7z`
- local Rec Room export folders such as `AvatarData*/`
- local third-party addon folders such as `vendor/`

Do not commit personal avatar exports, generated VRM files, or release zips to the repository.
