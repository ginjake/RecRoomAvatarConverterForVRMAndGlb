# RecRoomAvatarConverterForVRMAndGlb

## Project Overview

This project converts official Rec Room avatar export `.glb` files into usable humanoid avatars for external platforms.

The converter automatically generates humanoid bones and rigging because the original Rec Room export is not directly suitable for VRM or Resonite use.

## Input Format

Input files are official Rec Room avatar export `.glb` files.

Do not assume the source model was manually authored.

## Output Formats

### VRM Output

The converter outputs:

* VRM 1.0

Primary use cases:

* cluster
* VTuber applications
* VRM-compatible platforms

The generated VRM must have valid Humanoid bone mappings.

### Rigged GLB Output

The converter also outputs:

* Rigged GLB for Resonite

This is not merely the original Rec Room export.
The converter should add humanoid bones and rigging so the avatar can be used as an animated character.

### Blender Output

The converter may output `.blend` files for inspection and debugging.

Use Blender output to inspect:

* bone placement
* rigging issues
* mesh problems
* export artifacts

## Pose Support

The converter should support both:

* T-Pose
* A-Pose

Sample avatars are stored in:

* `testAvatar/TPose`
* `testAvatar/APose`

Do not assume all Rec Room exports are T-Pose.

When changing rigging or conversion logic, check both pose types when possible.

## Known Issue / Investigation Area

Generated avatars may contain an unexpected point, marker, helper object, vertex artifact, or similar issue near the feet.

When investigating this:

* inspect the generated VRM
* inspect the generated rigged GLB
* inspect the generated Blender file
* identify whether the cause is mesh generation, bone generation, helper objects, or export processing

Do not remove legitimate avatar geometry.

## Current Limitations

Known limitations:

* Leg-supported Rec Room avatars are not currently supported.
* Blender 5.1 is the target version.

## Development Rules

Before proposing or making changes:

* Inspect relevant source files first.
* Do not guess implementation details.
* Clearly distinguish verified facts from hypotheses.
* Do not claim code was tested unless it was actually executed.
* Prefer minimal, targeted changes.
* Preserve backward compatibility where possible.

When changing behavior, explain the effect on:

* VRM 1.0 output
* Rigged GLB output
* Blender output
