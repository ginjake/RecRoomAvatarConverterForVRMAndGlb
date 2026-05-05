<img width="1536" height="1024" alt="ChatGPT Image 2026年4月30日 18_48_51" src="https://github.com/user-attachments/assets/5232cab2-9941-4ea9-b5af-a17a17ee9439" />


# Rec Room VRM Converter

## 日本語

Rec Roomのアバター書き出し `.glb` を、clusterで扱いやすいHumanoid VRM、またはResoniteなどで扱いやすいリグ付きGLBに変換するWindows向けツールです。

利用者はコマンド操作やPython環境の作成をする必要はありません。配布版zipを展開して、`RecRoomVrmConverter.exe` を起動するだけで使えます。

### 必要なもの

- Windows
- Blender 5.1
- Rec RoomからExportしたアバター `.glb`

Blender 5.1で動作確認しています。Blenderの画面を開いて操作する必要はありませんが、変換処理の内部でBlender 5.1を使用します。

VRM Addonは通常、手動で指定する必要はありません。配布版には変換に必要なVRM Addonを同梱し、変換時にBlender側で自動有効化します。

### 使い方

1. Rec RoomからアバターをExportします。

   足付きのアバターには対応していません。  
   **TPoseで出力してください。**  

   <img width="1749" height="1054" alt="Rec Room avatar export settings" src="https://github.com/user-attachments/assets/ff569f31-e229-4bc2-a717-dcf3ebb27db0" />

3. Blender 5.1をインストールします。

   https://www.blender.org/download/

4. GitHub Releasesから配布用zipをダウンロードします。

   [RecRoomVrmConverter.zip](https://github.com/ginjake/RecRoomAvatarConverterForVRMAndGlb/releases/tag/1.02)

5. zipを展開します。

6. `RecRoomVrmConverter.exe` を起動します。

7. 変換元のGLBと、出力先のVRMを選びます。

8. `Convert` を押します。

   <img width="887" height="641" alt="Rec Room VRM Converter UI" src="https://github.com/user-attachments/assets/c9e48e44-2929-4e0e-80be-8656c9e5c4ba" />

9. VRM、リグ付きGLB、確認用blendファイルが生成されていれば成功です。

### 出力されるファイル

- `.vrm`
- `.rigged.glb`
- `.blend`

`.blend` は確認用です。Blenderで開くと、生成されたリグ、メッシュ統合、ウェイトを確認できます。

### 制限

- 足付きのRec Roomアバターには非対応です。
- Rec Roomの標準的な上半身アバター書き出しを対象にしています。
- 足ボーンはclusterなどのHumanoid判定用のプレースホルダーです。
- 複雑な衣装、髪、帽子、髭、アクセサリでは、メッシュ分類やウェイトに追加調整が必要になる場合があります。

### ライセンス

このプロジェクト本体はMITライセンスで公開しています。詳しくは `LICENSE` を参照してください。

配布版には、VRMの作成とエクスポートのために [VRM Add-on for Blender](https://github.com/saturday06/VRM-Addon-for-Blender) を同梱します。

VRM Add-on for Blenderは `MIT OR GPL-3.0-or-later` のデュアルライセンスです。このプロジェクトの配布版ではMITライセンスとして同梱します。

配布物には、VRM Add-on for Blender由来の次のライセンス・通知ファイルを含めます。

- `vendor/VRM-Addon-for-Blender/LICENSE_MAIN.txt`
- `vendor/VRM-Addon-for-Blender/LICENSE_(OPTION1)_MIT.txt`
- `vendor/VRM-Addon-for-Blender/LICENSE_(OPTION2)_GPL-3_0.txt`
- `vendor/VRM-Addon-for-Blender/Notice.txt`



## English

Rec Room VRM Converter is a Windows tool that converts Rec Room avatar export `.glb` files into Humanoid VRM files for cluster, or rigged GLB files for platforms such as Resonite.

End users do not need to use commands or set up Python. Download the release zip, extract it, and run `RecRoomVrmConverter.exe`.

### Requirements

- Windows
- Blender 5.1
- A Rec Room avatar export `.glb`

This tool is tested with Blender 5.1. You do not need to operate Blender manually, but the converter uses Blender 5.1 internally.

Normally, you do not need to select a VRM Addon manually. The release package includes the VRM Addon required for conversion, and the converter enables it in Blender automatically.

### How to Use

1. Export your avatar from Rec Room.

   Avatars with legs are not supported.  
   **Please export in T-pose.**

   <img width="1749" height="1054" alt="Rec Room avatar export settings" src="https://github.com/user-attachments/assets/ff569f31-e229-4bc2-a717-dcf3ebb27db0" />

3. Install Blender 5.1.

   https://www.blender.org/download/

4. Download the release zip from GitHub Releases.

   [RecRoomVrmConverter.zip](https://github.com/ginjake/RecRoomAvatarConverterForVRMAndGlb/releases/tag/1.0)

5. Extract the zip.

6. Run `RecRoomVrmConverter.exe`.

7. Select the input GLB and the output VRM path.

8. Click `Convert`.

   <img width="887" height="641" alt="Rec Room VRM Converter UI" src="https://github.com/user-attachments/assets/c9e48e44-2929-4e0e-80be-8656c9e5c4ba" />

9. The conversion is successful if the VRM, rigged GLB, and inspection blend file are generated.

### Output Files

- `.vrm`
- `.rigged.glb`
- `.blend`

The `.blend` file is for inspection. You can open it in Blender to check the generated rig, merged meshes, and weights.

### Limitations

- Rec Room avatars with legs are not supported.
- This tool targets the standard upper-body Rec Room avatar export layout.
- Leg bones are placeholders for Humanoid validation on platforms such as cluster.
- Complex outfits, hair, hats, beards, or accessories may still require additional mesh classification or weight adjustments.

### License

This project itself is released under the MIT License. See `LICENSE` for details.

The release package includes [VRM Add-on for Blender](https://github.com/saturday06/VRM-Addon-for-Blender) to create and export VRM files.

VRM Add-on for Blender is dual-licensed under `MIT OR GPL-3.0-or-later`. This project's release package includes it under the MIT license.

The release package includes the following license and notice files from VRM Add-on for Blender:

- `vendor/VRM-Addon-for-Blender/LICENSE_MAIN.txt`
- `vendor/VRM-Addon-for-Blender/LICENSE_(OPTION1)_MIT.txt`
- `vendor/VRM-Addon-for-Blender/LICENSE_(OPTION2)_GPL-3_0.txt`
- `vendor/VRM-Addon-for-Blender/Notice.txt`


