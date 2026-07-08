# SPDX-License-Identifier: MIT

bl_info = {
    "name": "GP Tool Presets",
    "author": "Dk",
    "version": (1, 0, 0),
    "blender": (5, 1, 0),
    "location": "View3D > Sidebar > GP Presets",
    "description": "Save and apply Grease Pencil tool settings as reusable presets.",
    "category": "Grease Pencil",
}

import bpy

from .operators import (
    GPTOOLPRESETS_OT_save_new,
    GPTOOLPRESETS_OT_update_selected,
    GPTOOLPRESETS_OT_apply,
    GPTOOLPRESETS_OT_rename,
    GPTOOLPRESETS_OT_delete,
    GPTOOLPRESETS_OT_duplicate,
    GPTOOLPRESETS_OT_move_up,
    GPTOOLPRESETS_OT_move_down,
    GPTOOLPRESETS_OT_export,
    GPTOOLPRESETS_OT_import,
    GPTOOLPRESETS_OT_copy_hex,
)
from .ui import GPTOOLPRESETS_UL_presets, GPTOOLPRESETS_PT_panel


class GPToolPresetItem(bpy.types.PropertyGroup):
    name: bpy.props.StringProperty(name="Name", default="Preset")
    data_json: bpy.props.StringProperty(name="Preset Data", default="{}")


class GPToolPresetsPreferences(bpy.types.AddonPreferences):
    bl_idname = __package__
    presets: bpy.props.CollectionProperty(type=GPToolPresetItem)
    active_index: bpy.props.IntProperty(default=0)
    last_applied: bpy.props.StringProperty(name="Last Applied", default="")
    stroke_preview: bpy.props.FloatVectorProperty(
        name="Stroke Preview",
        subtype="COLOR",
        size=4,
        min=0.0,
        max=1.0,
        default=(0.0, 0.0, 0.0, 1.0),
    )
    fill_preview: bpy.props.FloatVectorProperty(
        name="Fill Preview",
        subtype="COLOR",
        size=4,
        min=0.0,
        max=1.0,
        default=(0.0, 0.0, 0.0, 1.0),
    )

    def draw(self, context):
        self.layout.label(text="Use View3D > Sidebar > GP Presets.")


classes = (
    GPToolPresetItem,
    GPToolPresetsPreferences,
    GPTOOLPRESETS_UL_presets,
    GPTOOLPRESETS_OT_save_new,
    GPTOOLPRESETS_OT_update_selected,
    GPTOOLPRESETS_OT_apply,
    GPTOOLPRESETS_OT_rename,
    GPTOOLPRESETS_OT_delete,
    GPTOOLPRESETS_OT_duplicate,
    GPTOOLPRESETS_OT_move_up,
    GPTOOLPRESETS_OT_move_down,
    GPTOOLPRESETS_OT_export,
    GPTOOLPRESETS_OT_import,
    GPTOOLPRESETS_OT_copy_hex,
    GPTOOLPRESETS_PT_panel,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
