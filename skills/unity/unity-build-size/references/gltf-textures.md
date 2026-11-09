# glTF textures in a Unity build (glTFast)

Read this when `scripts/check_unity_build_size.py` reports `gltf-embedded-texture` or
`gltf-embedded-images`, or when the Build Report lists `.glb`/`.gltf` files near the top.
Checked against **glTFast 6.20.0** (`com.unity.cloud.gltfast`) on **Unity 6000.5.10f1**; the
behavior comes from the package, so read the package version in `Packages/packages-lock.json`
before relying on it.

## Why embedded images are large

glTFast imports a `.glb`/`.gltf` with a `ScriptedImporter`. How each image arrives decides how it
ships:

| Image in the model | How glTFast 6.20 loads it in the Editor | What ships |
|--------------------|------------------------------------------|------------|
| Inside the file (a `bufferView` in a `.glb`, or a `data:` URI) | Decoded with `Texture2D.LoadImage`, then added to the model as a sub-asset | Uncompressed: PNG becomes 32-bit RGBA, JPEG becomes RGB24, with a full mip chain |
| A separate file next to a `.gltf` (`"uri": "wood.png"`) that is already in `Assets/` | `AssetDatabase.LoadAssetAtPath<Texture2D>` on that file | Whatever its Texture Importer says: compressed by default |

Sources in the package: `Runtime/Scripts/ImageConversionImageLoader.cs` (the `LoadImage` call),
`Editor/Scripts/EditorDownloadProvider.cs` (`SyncTextureLoader` loads external images from the
asset database), and `Editor/Scripts/GltfImporter.cs` (only textures without an asset path are
added as sub-assets). The importer has no compression or max-size setting for embedded images.

Measured with one 512×512 JPEG on Windows Standalone: embedded in the `.glb` it was `RGB24`;
moved next to a `.gltf` it was `DXT1`. A full mip chain adds a third, so an uncompressed texture
costs `width × height × bytes-per-pixel × 4/3`:

| Edge | RGB24 (JPEG) | RGBA32 (PNG) |
|------|--------------|--------------|
| 512 | 1.0 MB | 1.3 MB |
| 1024 | 4.0 MB | 5.3 MB |
| 2048 | 16.0 MB | 21.3 MB |
| 4096 | 64.0 MB | 85.3 MB |
| 8192 | 256.0 MB | 341.3 MB |

(MB here is 1024² bytes.) A model with three 8K maps costs close to 1 GB before anything else.

## Fix A — shrink the images inside the model (smallest change)

[glTF Transform](https://gltf-transform.dev/cli)'s `resize` command scales PNG and JPEG
textures down in place and never scales one up. It keeps the aspect ratio and leaves meshes and
materials untouched. Commit or back up first; the command overwrites the file when input and
output are the same. Commands here were run with CLI 4.5.1 (`@gltf-transform/cli@4`; needs
Node.js).

```bash
# One model, every texture at most 1024 px on its longest edge
npx @gltf-transform/cli@4 resize model.glb model.glb --width 1024 --height 1024
```

`resize --pattern` matches images by name or URI only. Images embedded in exported `.glb` files
often have neither, and then the pattern matches nothing without an error; check the output with
`scripts/check_unity_build_size.py` instead of assuming it worked.

Every model in a project, from the project root (POSIX shell; on Windows PowerShell, loop over
`Get-ChildItem Assets -Recurse -Filter *.glb` instead):

```bash
find Assets -iname '*.glb' -print0 | while IFS= read -r -d '' f; do
  npx @gltf-transform/cli@4 resize "$f" "$f" --width 1024 --height 1024
done
```

The textures still ship uncompressed, so pick the edge from the table above. Unity reimports the
models the next time the Editor gets focus, or at the start of a batch-mode run.

**A `.gltf` input is different.** When `resize` writes a `.gltf`, it writes every image, including
`data:` URIs, as a separate file next to it. The images then import through the Texture Importer,
which is Fix B below: they get compressed, but also arrive with sRGB on. Follow the sRGB step in
Fix B for those files. Only a `.glb` keeps its images embedded after Fix A.

## Fix B — move the images out so the Texture Importer compresses them

`gltf-transform copy` writes a `.gltf` with its buffer and images as separate files:

```bash
npx @gltf-transform/cli@4 copy model.glb Assets/Models/Model/model.gltf
```

Delete the old `.glb` (and its `.meta`) only after the new model works in every scene that used
it: the `.gltf` gets a new GUID, so every prefab or scene reference to the `.glb` must be
re-pointed.

Each image is now its own texture asset with Unity's default import settings: compressed, Max Size
2048, and **sRGB (Color Texture) on**. That color setting is wrong for data textures. glTFast
treats only these as sRGB (`GltfImport.cs`, the texture gamma pass):

- `baseColorTexture`, `emissiveTexture`;
- with `KHR_materials_pbrSpecularGlossiness`: `diffuseTexture` and `specularGlossinessTexture`.

Turn **sRGB (Color Texture) off** on every other texture the model uses: normal,
metallic-roughness, occlusion, and any extension's data maps. In the probe above, the normal maps
arrived as `Default` with sRGB on, which shades wrong in a Linear-color-space project. glTFast
samples the embedded versions as plain linear textures, so leaving Texture Type at `Default` with
sRGB off matches what the embedded import did. Compare the model against the embedded original in
the same scene and light before deleting the `.glb`.

Fix B gives real block compression (several times smaller than Fix A at the same resolution) and
per-platform overrides, at the cost of more files and the color-space step.

## Heavy geometry

`gltf-heavy-geometry` means the model's buffers hold more than images. glTFast turns that data
into Unity meshes of about the same size, and the Model Importer's **Mesh Compression** does not
apply because glTFast is not the Model Importer. Reduce the source instead:

```bash
npx @gltf-transform/cli@4 simplify model.glb model.glb --ratio 0.5
```

`simplify` stops early when it would exceed its `--error` limit, so check the result in the scene
and keep the original in version control.
