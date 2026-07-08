# GP Tool Presets

**GP Tool Presets** is a Blender extension for saving and reapplying Grease Pencil tool setups.

It is designed for 2D artists, animators, comic creators, and Grease Pencil users who switch between many drawing setups and do not want to keep manually rebuilding brush/tool settings.

---

## What It Does

GP Tool Presets lets you save the current Grease Pencil tool setup as a reusable preset, then apply it later.

A preset can store useful tool/brush values such as:

- Active tool ID
- Source brush name
- Brush size
- Brush strength
- Brush hardness
- Brush spacing
- Pressure toggles where exposed
- Stabilizer / smooth stroke values where exposed
- Grease Pencil brush settings where Blender exposes them
- Tool setting values where Blender exposes them
- Material name as reference
- Stroke color reference
- Fill color reference
- Stroke/fill hex values

The extension can be useful for presets such as:

- Clean ink
- Soft sketch
- Rough blocking
- Shading brush
- Eraser setup
- Fill setup
- Curve tool setup
- Circle tool setup
- Box tool setup
- Other Grease Pencil tool configurations

---

### Screenshot

![sc1.png](sc1.png)

--- 

## Core Design

This extension intentionally uses a safe design.

```text
Presets save values.
One GP Tool Preset brush receives the applied values.
Materials are reference-only.
```

Earlier test designs attempted to create material copies or one brush per preset. That caused unwanted side effects. The final design avoids that.

---

## One Runtime Brush

The extension uses one reusable brush:

```text
GP Tool Preset
```

When you apply any preset, the saved values are applied to that one brush.

This avoids creating many brush entries like:

```text
GP Tool Preset - Soft Airbrush
GP Tool Preset - Clean Ink
GP Tool Preset - Sketch Brush
```

The goal is to keep the toolbar clean and predictable.

---

## Material Workflow

GP Tool Presets does **not** manage Grease Pencil materials.

It does not:

- Create materials
- Duplicate materials
- Edit materials
- Delete materials
- Recreate missing materials
- Change already drawn strokes

Instead, each preset stores material information as reference data only:

- Material name
- Stroke color
- Fill color
- Stroke hex value
- Fill hex value

When applying a preset:

- If the saved material already exists in the current Blender file, the extension tries to select it.
- If the material does not exist, material switching is skipped.
- The saved stroke/fill colors remain visible in the preset info panel.
- Users can recreate materials manually using the color swatches or hex copy buttons.

This protects existing Grease Pencil artwork. Grease Pencil strokes reference material data-blocks, so automatic material editing can accidentally change old strokes.

---

## Color Reference

The preset info panel shows saved material colors as:

```text
Stroke: [color preview] #HEX [Copy]
Fill:   [color preview] #HEX [Copy]
```

The swatches are visual previews.

For exact color recreation, use the copy button beside the hex value.

```text
Use Copy for exact color. Swatches are visual previews.
```

Hex values are widely supported across graphics programs and are the safest way to recreate the same color manually.

---

## Main Features

### Save Current as New

Creates a new preset from the current Grease Pencil tool setup.

Use this when you want to save a new drawing setup.

---

### Apply

Applies the selected preset to the reusable `GP Tool Preset` brush.

The extension will also try to switch to the saved material if it already exists in the file.

---

### Update Selected

Overwrites the selected preset with the current tool setup.

A confirmation popup appears before the overwrite happens.

This protects users from accidentally replacing a saved preset.

---

### Delete

Deletes the selected preset entry.

A confirmation popup appears before deleting because Blender undo may not restore extension preset data.

Deleting a preset does **not** delete brushes or materials.

---

### Duplicate

Creates a copy of the selected preset.

This is useful before experimenting with changes.

---

### Rename

Renames the selected preset.

---

### Move Up / Move Down

Reorders presets in the list.

---

### Export / Import

Exports and imports preset libraries as JSON files.

This is useful for:

- Moving presets between projects
- Backing up presets
- Sharing preset packs
- Keeping different workflow sets

---

## Sidebar Location

After installing and enabling the extension:

```text
View3D > Sidebar > GP Presets
```

Open the sidebar with `N` in the 3D Viewport, then select the **GP Presets** tab.

---

## Preset Info Panel

The selected preset displays useful information, including:

- Tool
- Source brush
- Runtime brush
- Material name
- Stroke color swatch
- Stroke hex value
- Fill color swatch
- Fill hex value
- Brush size
- Brush strength
- Brush hardness
- Brush spacing
- Stabilizer state
- Stabilizer radius
- Stabilizer factor
- Pressure size
- Pressure strength
- Blender version used when saved

This helps users understand what a preset contains before applying it.

---

## Recommended Workflow

### Saving a Preset

1. Select a Grease Pencil object.
2. Choose the tool/brush you want.
3. Adjust the brush/tool settings.
4. Select the material you want as a reference.
5. Click **Save Current as New**.
6. Name the preset.

---

### Applying a Preset

1. Select the preset from the list.
2. Click **Apply**.
3. The extension applies the saved values to `GP Tool Preset`.
4. Continue drawing with the `GP Tool Preset` brush.

---

### Recreating Missing Materials

If a preset references a material that does not exist in the current project:

1. Look at the saved Stroke and Fill swatches.
2. Use the copy buttons beside the hex values.
3. Create a Grease Pencil material manually.
4. Paste or use the copied color values.
5. Save the material in your project or asset library if needed.

---

## What the Extension Does Not Do

GP Tool Presets intentionally avoids risky behavior.

It does not:

- Execute drawing commands
- Draw strokes for the user
- Delete user materials
- Delete user brushes
- Automatically create missing materials
- Automatically duplicate materials
- Automatically edit existing materials
- Manage Blender material asset libraries
- Replace Blender’s own brush or material systems

---

## Why Materials Are Reference-Only

Grease Pencil materials are shared data-blocks. If an extension edits a material that existing strokes use, those old strokes can visually change.

To avoid that, this extension only stores material reference information.

For reusable material libraries, use Blender’s own material/asset workflows.

---

## Compatibility Notes

This version was developed for Blender 5.1+ Grease Pencil workflows.

Blender 5.2 may change some Grease Pencil API details. If Blender changes property names, tool paths, or brush activation behavior, a compatibility update may be needed.

The extension is designed so future compatibility work should mostly involve updating property paths rather than redesigning the full workflow.

---

## Installation

1. Download the release `.zip`.
2. Open Blender.
3. Go to:

```text
Edit > Preferences > Extensions
```

4. Install the extension from the `.zip`.
5. Enable **GP Tool Presets**.
6. Open:

```text
View3D > Sidebar > GP Presets
```

---

## Exported Preset Files

Preset exports are JSON files.

They contain stored values such as:

- Preset names
- Tool identifiers
- Brush setting values
- Material reference names
- Stroke/fill color reference values

They do not contain real Blender material data-blocks or external assets.

---

## Safety Rules

The extension follows these rules:

```text
One visible extension brush only.
Presets store values only.
Materials are reference-only.
Deleting presets does not delete Blender data-blocks.
Updating presets requires confirmation.
Deleting presets requires confirmation.
```

These rules are meant to protect user artwork and avoid toolbar/material clutter.

---

## Version History

### v1.0.0

First official release.

Finalized stable design:

- One reusable `GP Tool Preset` brush
- Presets save tool/brush values
- Materials are reference-only
- Stroke/fill color swatches
- Stroke/fill hex copy buttons
- Confirmation before update
- Confirmation before delete
- Import/export support
- Reorderable preset list
- Detailed preset info panel

---

## License

MIT License.
