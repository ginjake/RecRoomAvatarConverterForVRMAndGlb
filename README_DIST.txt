Rec Room VRM Converter
======================

日本語
------

Rec Roomのアバター書き出し .glb を、clusterで扱いやすいHumanoid VRM、
またはResoniteなどで扱いやすいリグ付きGLBに変換するWindows向けツールです。

コマンド操作やPython環境の作成は不要です。
このフォルダ内の RecRoomVrmConverter.exe を起動して使用してください。

必要なもの:
- Windows
- Blender 5.1
- Rec RoomからExportしたアバター .glb

Blender 5.1で動作確認しています。
Blenderの画面を開いて操作する必要はありませんが、変換処理の内部でBlender 5.1を使用します。

VRM Addonは通常、手動で指定する必要はありません。
この配布版には変換に必要なVRM Addonを同梱し、変換時にBlender側で自動有効化します。

使い方:
1. Rec RoomからアバターをExportします。
   足付きのアバターには対応していません。
2. Blender 5.1をインストールします。
   https://www.blender.org/download/
3. RecRoomVrmConverter.exe を起動します。
4. Input GLB に、読み込むRecRoomアバターの .glb を指定します。
5. 保存先に、出力先の .vrm を指定します。
6. Convert を押します。
7. .vrm、.rigged.glb、.blend が生成されていれば成功です。

出力されるファイル:
- .vrm
- .rigged.glb
- .blend

.blend は確認用です。Blenderで開くと、生成されたリグ、メッシュ統合、ウェイトを確認できます。

制限:
- 足付きのRec Roomアバターには非対応です。
- Rec Roomの標準的な上半身アバター書き出しを対象にしています。
- 足ボーンはclusterなどのHumanoid判定用のプレースホルダーです。
- 複雑な衣装、髪、帽子、髭、アクセサリでは、メッシュ分類やウェイトに追加調整が必要になる場合があります。


English
-------

Rec Room VRM Converter is a Windows tool that converts Rec Room avatar export .glb files
into Humanoid VRM files for cluster, or rigged GLB files for platforms such as Resonite.

You do not need to use commands or set up Python.
Run RecRoomVrmConverter.exe in this folder.

Requirements:
- Windows
- Blender 5.1
- A Rec Room avatar export .glb

This tool is tested with Blender 5.1.
You do not need to operate Blender manually, but the converter uses Blender 5.1 internally.

Normally, you do not need to select a VRM Addon manually.
This package includes the VRM Addon required for conversion, and the converter enables it in Blender automatically.

How to use:
1. Export your avatar from Rec Room.
   Avatars with legs are not supported.
2. Install Blender 5.1.
   https://www.blender.org/download/
3. Run RecRoomVrmConverter.exe.
4. Select your Rec Room avatar .glb in Input GLB.
5. Select the output .vrm path.
6. Click Convert.
7. The conversion is successful if .vrm, .rigged.glb, and .blend files are generated.

Output files:
- .vrm
- .rigged.glb
- .blend

The .blend file is for inspection. You can open it in Blender to check the generated rig,
merged meshes, and weights.

Limitations:
- Rec Room avatars with legs are not supported.
- This tool targets the standard upper-body Rec Room avatar export layout.
- Leg bones are placeholders for Humanoid validation on platforms such as cluster.
- Complex outfits, hair, hats, beards, or accessories may still require additional mesh classification or weight adjustments.


License
-------

Rec Room VRM Converter is released under the MIT License.

MIT License

Copyright (c) 2026 ginjake

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.


Third-party software
--------------------

This package includes VRM Add-on for Blender to create and export VRM files.

VRM Add-on for Blender:
https://github.com/saturday06/VRM-Addon-for-Blender

VRM Add-on for Blender is dual-licensed under MIT OR GPL-3.0-or-later.
This package includes it under the MIT license.

The original VRM Add-on for Blender license and notice files are included in:
_internal\vendor\VRM-Addon-for-Blender\

- LICENSE_MAIN.txt
- LICENSE_(OPTION1)_MIT.txt
- LICENSE_(OPTION2)_GPL-3_0.txt
- Notice.txt

