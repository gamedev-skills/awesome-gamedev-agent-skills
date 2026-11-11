# glTF textures in a Unity build (glTFast)

Read this when `scripts/check_unity_build_size.py` reports `gltf-embedded-texture`,
`gltf-embedded-images` or `gltf-heavy-geometry`, or when the Build Report lists `.glb`/`.gltf`
files near the top. Checked against **glTFast 6.20.0** (`com.unity.cloud.gltfast`) on **Unity
6000.5.10f1** and **glTF Transform CLI 4.5.1**. The behavior comes from the package, so read its
version in `Packages/packages-lock.json` first.

Contents: why embedded images are large · Fix A (shrink inside the model) · Fix B (move the images
out) · heavy geometry.

## Why embedded images are large

glTFast imports a `.glb`/`.gltf` with a `ScriptedImporter`. How each image arrives decides how it
ships:

| Image in the model | How glTFast 6.20 loads it in the Editor | What ships |
|--------------------|------------------------------------------|------------|
| Inside the file (a `bufferView` in a `.glb`, or a `data:` URI) | Decoded with `Texture2D.LoadImage`, then added to the model as a sub-asset | Uncompressed: PNG becomes 32-bit RGBA, JPEG becomes RGB24, with mipmaps (the importer's default) |
| A separate file next to a `.gltf` (`"uri": "wood.png"`) that is already in `Assets/` | `AssetDatabase.LoadAssetAtPath<Texture2D>` on that file | Whatever its Texture Importer says: compressed by default |

Sources in the package: `Runtime/Scripts/ImageConversionImageLoader.cs` (the `LoadImage` call),
`Editor/Scripts/EditorDownloadProvider.cs` (external images come from the asset database),
`Editor/Scripts/GltfImporter.cs` (only textures without an asset path become sub-assets; mipmaps
on by default). The importer has no compression or max-size setting for embedded images.

Measured with one 512×512 JPEG on Windows Standalone: embedded in the `.glb` it was `RGB24`;
moved next to a `.gltf` it was `DXT1`. Mipmaps add a third, so an uncompressed texture costs
`width × height × bytes-per-pixel × 4/3`:

| Edge | RGB24 (JPEG) | RGBA32 (PNG) |
|------|--------------|--------------|
| 512 | 1.0 MB | 1.3 MB |
| 1024 | 4.0 MB | 5.3 MB |
| 2048 | 16.0 MB | 21.3 MB |
| 4096 | 64.0 MB | 85.3 MB |
| 8192 | 256.0 MB | 341.3 MB |

(MB here is 1024² bytes.) A model with three 8K maps costs close to 1 GB before anything else.

## Fix A: shrink the images inside the model (smallest change)

[glTF Transform](https://gltf-transform.dev/cli)'s `resize` scales PNG and JPEG textures down,
keeps the aspect ratio and never scales up. Commit or back up first: with the same input and
output path it overwrites the model. Needs Node.js.

```bash
# One model, every texture at most 1024 px on its longest edge
npx @gltf-transform/cli@4 resize model.glb model.glb --width 1024 --height 1024
```

Every `.glb` in a project, from the project root (bash; in PowerShell loop over
`Get-ChildItem Assets -Recurse -Filter *.glb`):

```bash
find Assets -iname '*.glb' -not -path 'Assets/StreamingAssets/*' -print0 |
  while IFS= read -r -d '' f; do
    npx @gltf-transform/cli@4 resize "$f" "$f" --width 1024 --height 1024
  done
```

The textures still ship uncompressed, so pick the edge from the table. Unity reimports the models
the next time the Editor gets focus, or at the start of a batch-mode run.

- `resize --pattern` matches images by name or URI only. Embedded images in exported `.glb` files
  often have neither, and then nothing matches and nothing reports an error. Rerun the checker
  instead of assuming it worked.
- **A `.gltf` input becomes Fix B.** When `resize` writes a `.gltf`, it writes every image,
  `data:` URIs included, as a separate file next to it, named after the texture slot
  (`baseColor_1.png`, `normal_1.png`, ...), and it overwrites files with those names. Two
  `.gltf` files in one folder therefore end up pointing at the same images, the last model's.
  Move each `.gltf` with its `.meta` into its own folder first (the checker prints the path), then
  follow the sRGB step in Fix B. Only a `.glb` keeps its images embedded after Fix A.

## Fix B: move the images out so the Texture Importer compresses them

`gltf-transform copy` writes a `.gltf` with its buffer and images as separate files. Give it a
folder of its own, for the naming reason above:

```bash
npx @gltf-transform/cli@4 copy model.glb Assets/Models/Model/model.gltf
```

The `.gltf` gets a new GUID, so every prefab or scene reference to the `.glb` must be re-pointed.
Delete the old `.glb` and its `.meta` only after the new model works in every scene that used it.

Each image is now its own texture asset with Unity's default import settings: compressed, Max Size
2048, and **sRGB (Color Texture) on**. That color setting is wrong for data textures. glTFast
treats only these as sRGB (`GltfImport.cs`, the texture gamma pass):

- `baseColorTexture`, `emissiveTexture`;
- with `KHR_materials_pbrSpecularGlossiness`: `diffuseTexture` and `specularGlossinessTexture`.

Turn **sRGB (Color Texture) off** on every other texture the model uses: normal,
metallic-roughness, occlusion, and any extension's data maps. In the probe, the normal maps
arrived as `Default` with sRGB on, which shades wrong in a Linear-color-space project. glTFast
samples the embedded versions as plain linear textures, so Texture Type `Default` with sRGB off
matches what the embedded import did. Compare the model with the embedded original in the same
scene and light before deleting the `.glb`.

Fix B gives real block compression (several times smaller than Fix A at the same resolution) and
per-platform overrides, at the cost of more files and the color-space step.

## Heavy geometry

`gltf-heavy-geometry` means the model's buffers hold more than images. glTFast turns that data
into Unity meshes of about the same size, and the Model Importer's **Mesh Compression** does not
apply because glTFast is not the Model Importer. Reduce the source. `weld` first, because split
vertices stop the simplifier early, and loosen `--error` (the default 0.0001 often stops it well
short of the ratio):

```bash
npx @gltf-transform/cli@4 weld model.glb model.glb
npx @gltf-transform/cli@4 simplify model.glb model.glb --ratio 0.5 --error 0.001
```

Check the silhouette in the scene and keep the original in version control.
