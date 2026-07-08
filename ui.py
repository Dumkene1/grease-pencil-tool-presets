# SPDX-License-Identifier: MIT

import bpy
from .preset_utils import get_addon_preferences, preset_from_json, preset_summary


class GPTOOLPRESETS_UL_presets(bpy.types.UIList):
    bl_idname = "GPTOOLPRESETS_UL_presets"

    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        row = layout.row(align=True)
        row.prop(item, "name", text="", emboss=False, icon="PRESET")


class GPTOOLPRESETS_PT_panel(bpy.types.Panel):
    bl_label = "GP Tool Presets"
    bl_idname = "GPTOOLPRESETS_PT_panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "GP Presets"

    @classmethod
    def poll(cls, context):
        return True

    def draw(self, context):
        prefs = get_addon_preferences(context)
        layout = self.layout
        if prefs is None:
            layout.label(text="Preferences not found.", icon="ERROR")
            return

        row = layout.row()
        row.template_list("GPTOOLPRESETS_UL_presets", "", prefs, "presets", prefs, "active_index", rows=7)

        col = row.column(align=True)
        col.operator("gp_tool_presets.move_up", text="", icon="TRIA_UP")
        col.operator("gp_tool_presets.move_down", text="", icon="TRIA_DOWN")

        layout.separator()
        layout.operator("gp_tool_presets.apply", icon="CHECKMARK")

        row = layout.row(align=True)
        row.operator("gp_tool_presets.save_new", icon="ADD")
        row.operator("gp_tool_presets.update_selected", icon="FILE_REFRESH")

        row = layout.row(align=True)
        row.operator("gp_tool_presets.duplicate", icon="DUPLICATE")
        row.operator("gp_tool_presets.rename", icon="GREASEPENCIL")
        row.operator("gp_tool_presets.delete", icon="TRASH")

        row = layout.row(align=True)
        row.operator("gp_tool_presets.export", icon="EXPORT")
        row.operator("gp_tool_presets.import", icon="IMPORT")

        if getattr(prefs, "last_applied", ""):
            layout.label(text=f"Last Applied: {prefs.last_applied}", icon="CHECKMARK")

        if prefs.presets and 0 <= prefs.active_index < len(prefs.presets):
            data = preset_from_json(prefs.presets[prefs.active_index].data_json)
            s = preset_summary(data)

            layout.separator()
            box = layout.box()
            box.label(text="Preset Info", icon="INFO")
            box.label(text=f"Tool: {s.get('tool_id') or '-'}")
            box.label(text=f"Source Brush: {s.get('source_brush') or '-'}")
            box.label(text=f"Runtime Brush: {s.get('runtime_brush') or '-'}")
            box.label(text=f"Material: {s.get('material') or '-'}")

            try:
                prefs.stroke_preview = s.get("stroke_color", (0.0, 0.0, 0.0, 1.0))
                prefs.fill_preview = s.get("fill_color", (0.0, 0.0, 0.0, 1.0))
            except Exception:
                pass

            color_box = layout.box()
            color_box.label(text="Saved Material Reference", icon="MATERIAL")

            row = color_box.row(align=True)
            row.prop(prefs, "stroke_preview", text="Stroke")
            value = s.get("stroke_hex", "")
            if value:
                row.label(text=value)
                op = row.operator("gp_tool_presets.copy_hex", text="", icon="COPYDOWN")
                op.value = value

            row = color_box.row(align=True)
            row.prop(prefs, "fill_preview", text="Fill")
            value = s.get("fill_hex", "")
            if value:
                row.label(text=value)
                op = row.operator("gp_tool_presets.copy_hex", text="", icon="COPYDOWN")
                op.value = value

            color_box.label(text="Use Copy for exact color. Swatches are visual previews.", icon="INFO")

            brush_box = layout.box()
            brush_box.label(text="Saved Brush Values", icon="BRUSH_DATA")
            grid = brush_box.grid_flow(columns=2, align=True)
            grid.label(text=f"Size: {s.get('size', '-')}")
            grid.label(text=f"Strength: {s.get('strength', '-')}")
            grid.label(text=f"Hardness: {s.get('hardness', '-')}")
            grid.label(text=f"Spacing: {s.get('spacing', '-')}")
            grid.label(text=f"Stabilizer: {s.get('stabilizer', '-')}")
            grid.label(text=f"Stab. Radius: {s.get('stabilizer_radius', '-')}")
            grid.label(text=f"Stab. Factor: {s.get('stabilizer_factor', '-')}")
            grid.label(text=f"Pressure Size: {s.get('pressure_size', '-')}")
            grid.label(text=f"Pressure Strength: {s.get('pressure_strength', '-')}")
            grid.label(text=f"Saved In: {s.get('saved_in', '-')}")
