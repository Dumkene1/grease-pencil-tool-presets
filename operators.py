# SPDX-License-Identifier: MIT

import json
import bpy
from bpy.props import StringProperty
from bpy_extras.io_utils import ExportHelper, ImportHelper

from .preset_utils import (
    capture_current_preset,
    apply_preset_data,
    preset_to_json,
    preset_from_json,
    get_addon_preferences,
)


def active_item(context):
    prefs = get_addon_preferences(context)
    if not prefs or not prefs.presets:
        return None, None
    prefs.active_index = max(0, min(prefs.active_index, len(prefs.presets) - 1))
    return prefs, prefs.presets[prefs.active_index]


class GPTOOLPRESETS_OT_save_new(bpy.types.Operator):
    bl_idname = "gp_tool_presets.save_new"
    bl_label = "Save Current as New"
    bl_description = "Save the current Grease Pencil tool setup as a preset"

    preset_name: StringProperty(name="Preset Name", default="New GP Preset")

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context):
        prefs = get_addon_preferences(context)
        if prefs is None:
            self.report({"ERROR"}, "Preferences not found.")
            return {"CANCELLED"}
        data = capture_current_preset(context, self.preset_name)
        item = prefs.presets.add()
        item.name = self.preset_name
        item.data_json = preset_to_json(data)
        prefs.active_index = len(prefs.presets) - 1
        self.report({"INFO"}, f"Saved preset: {self.preset_name}")
        return {"FINISHED"}


class GPTOOLPRESETS_OT_update_selected(bpy.types.Operator):
    bl_idname = "gp_tool_presets.update_selected"
    bl_label = "Update Selected"
    bl_description = "Overwrite the selected preset with the current Grease Pencil tool setup"

    def invoke(self, context, event):
        prefs, item = active_item(context)
        if item is None:
            self.report({"WARNING"}, "No preset selected.")
            return {"CANCELLED"}
        return context.window_manager.invoke_props_dialog(self, width=420)

    def draw(self, context):
        prefs, item = active_item(context)
        layout = self.layout
        layout.label(text="Update selected preset?", icon="QUESTION")
        if item is not None:
            layout.label(text=f"Preset: {item.name}")
        layout.label(text="This will replace its saved brush/tool values.")

    def execute(self, context):
        prefs, item = active_item(context)
        if item is None:
            self.report({"WARNING"}, "No preset selected.")
            return {"CANCELLED"}
        item.data_json = preset_to_json(capture_current_preset(context, item.name))
        self.report({"INFO"}, f"Updated preset: {item.name}")
        return {"FINISHED"}


class GPTOOLPRESETS_OT_apply(bpy.types.Operator):
    bl_idname = "gp_tool_presets.apply"
    bl_label = "Apply"
    bl_description = "Apply the selected preset to the GP Tool Preset brush"

    def execute(self, context):
        prefs, item = active_item(context)
        if item is None:
            self.report({"WARNING"}, "No preset selected.")
            return {"CANCELLED"}
        result = apply_preset_data(context, preset_from_json(item.data_json), prefs)
        skipped = result.get("skipped", [])
        if skipped:
            self.report({"INFO"}, f"Applied preset; skipped: {', '.join(skipped[:3])}")
        else:
            self.report({"INFO"}, f"Applied preset: {item.name}")
        return {"FINISHED"}


class GPTOOLPRESETS_OT_rename(bpy.types.Operator):
    bl_idname = "gp_tool_presets.rename"
    bl_label = "Rename"
    preset_name: StringProperty(name="New Name", default="Preset")

    def invoke(self, context, event):
        prefs, item = active_item(context)
        if item is None:
            return {"CANCELLED"}
        self.preset_name = item.name
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context):
        prefs, item = active_item(context)
        if item is None:
            return {"CANCELLED"}
        data = preset_from_json(item.data_json)
        item.name = self.preset_name
        data["name"] = self.preset_name
        item.data_json = preset_to_json(data)
        return {"FINISHED"}


class GPTOOLPRESETS_OT_delete(bpy.types.Operator):
    bl_idname = "gp_tool_presets.delete"
    bl_label = "Delete"
    bl_description = "Delete the selected preset"

    def invoke(self, context, event):
        prefs, item = active_item(context)
        if item is None:
            self.report({"WARNING"}, "No preset selected.")
            return {"CANCELLED"}
        return context.window_manager.invoke_props_dialog(self, width=420)

    def draw(self, context):
        prefs, item = active_item(context)
        layout = self.layout
        layout.label(text="Delete selected preset?", icon="ERROR")
        if item is not None:
            layout.label(text=f"Preset: {item.name}")
        layout.label(text="This cannot be restored with Blender Undo.")

    def execute(self, context):
        prefs, item = active_item(context)
        if item is None:
            return {"CANCELLED"}
        name = item.name
        idx = prefs.active_index
        prefs.presets.remove(idx)
        prefs.active_index = min(idx, max(0, len(prefs.presets) - 1))
        self.report({"INFO"}, f"Deleted preset: {name}")
        return {"FINISHED"}


class GPTOOLPRESETS_OT_duplicate(bpy.types.Operator):
    bl_idname = "gp_tool_presets.duplicate"
    bl_label = "Duplicate"

    def execute(self, context):
        prefs, item = active_item(context)
        if item is None:
            return {"CANCELLED"}
        data = preset_from_json(item.data_json)
        data["name"] = f"{item.name} Copy"
        new_item = prefs.presets.add()
        new_item.name = data["name"]
        new_item.data_json = preset_to_json(data)
        src = len(prefs.presets) - 1
        dst = prefs.active_index + 1
        prefs.presets.move(src, dst)
        prefs.active_index = dst
        return {"FINISHED"}


class GPTOOLPRESETS_OT_move_up(bpy.types.Operator):
    bl_idname = "gp_tool_presets.move_up"
    bl_label = "Move Up"

    def execute(self, context):
        prefs, item = active_item(context)
        if item is None or prefs.active_index <= 0:
            return {"CANCELLED"}
        idx = prefs.active_index
        prefs.presets.move(idx, idx - 1)
        prefs.active_index = idx - 1
        return {"FINISHED"}


class GPTOOLPRESETS_OT_move_down(bpy.types.Operator):
    bl_idname = "gp_tool_presets.move_down"
    bl_label = "Move Down"

    def execute(self, context):
        prefs, item = active_item(context)
        if item is None or prefs.active_index >= len(prefs.presets) - 1:
            return {"CANCELLED"}
        idx = prefs.active_index
        prefs.presets.move(idx, idx + 1)
        prefs.active_index = idx + 1
        return {"FINISHED"}


class GPTOOLPRESETS_OT_copy_hex(bpy.types.Operator):
    bl_idname = "gp_tool_presets.copy_hex"
    bl_label = "Copy Hex"
    bl_description = "Copy saved material hex value to clipboard"

    value: StringProperty(name="Hex Value", default="")

    def execute(self, context):
        if not self.value:
            self.report({"WARNING"}, "No hex value to copy.")
            return {"CANCELLED"}
        context.window_manager.clipboard = self.value
        self.report({"INFO"}, f"Copied {self.value}")
        return {"FINISHED"}


class GPTOOLPRESETS_OT_export(bpy.types.Operator, ExportHelper):
    bl_idname = "gp_tool_presets.export"
    bl_label = "Export Presets"
    filename_ext = ".json"
    filter_glob: StringProperty(default="*.json", options={"HIDDEN"})

    def execute(self, context):
        prefs = get_addon_preferences(context)
        data = {
            "addon": "GP Tool Presets",
            "schema_version": 9,
            "blender_version_exported": ".".join(str(x) for x in bpy.app.version),
            "presets": [preset_from_json(item.data_json) for item in prefs.presets],
        }
        with open(self.filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, sort_keys=True)
        return {"FINISHED"}


class GPTOOLPRESETS_OT_import(bpy.types.Operator, ImportHelper):
    bl_idname = "gp_tool_presets.import"
    bl_label = "Import Presets"
    filename_ext = ".json"
    filter_glob: StringProperty(default="*.json", options={"HIDDEN"})

    def execute(self, context):
        prefs = get_addon_preferences(context)
        with open(self.filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        count = 0
        for preset in data.get("presets", []):
            if isinstance(preset, dict):
                item = prefs.presets.add()
                item.name = preset.get("name") or "Imported Preset"
                item.data_json = preset_to_json(preset)
                count += 1
        if count:
            prefs.active_index = len(prefs.presets) - 1
        self.report({"INFO"}, f"Imported {count} preset(s).")
        return {"FINISHED"}
