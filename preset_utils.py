# SPDX-License-Identifier: MIT

import json
import bpy

SCHEMA_VERSION = 9
RUNTIME_BRUSH_NAME = "GP Tool Preset"

IMPORTANT_BRUSH_ATTRS = [
    "size", "strength", "hardness", "spacing", "jitter", "angle", "angle_factor",
    "use_pressure_size", "use_pressure_strength", "use_pressure_jitter",
    "use_pressure_spacing", "use_pressure_hardness",
    "use_smooth_stroke", "smooth_stroke_radius", "smooth_stroke_factor",
    "stroke_method", "direction", "use_scene_spacing", "use_space", "space",
    "use_locked_size", "falloff_shape",
]

KEYWORDS = (
    "size", "strength", "hardness", "spacing", "space", "angle", "aspect",
    "smooth", "stabil", "stroke", "post", "process", "simplify", "subdivision",
    "trim", "outline", "thickness", "random", "jitter", "radius", "factor",
    "rotation", "hue", "saturation", "value", "pressure", "fill", "gap",
    "extend", "dilate", "material", "opacity", "eraser", "grease", "gpencil",
    "curve", "falloff", "active_smooth",
)


def get_addon_preferences(context=None):
    context = context or bpy.context
    for key in ("gp_tool_presets", __package__):
        if key and key in context.preferences.addons:
            return context.preferences.addons[key].preferences
    for addon in context.preferences.addons:
        if addon.module.endswith("gp_tool_presets"):
            return addon.preferences
    return None


def safe_get(obj, attr, default=None):
    if obj is None or not hasattr(obj, attr):
        return default
    try:
        return getattr(obj, attr)
    except Exception:
        return default


def safe_set(obj, attr, value):
    if obj is None or not hasattr(obj, attr) or value is None:
        return False
    try:
        setattr(obj, attr, value)
        return True
    except Exception:
        return False


def to_json_value(value):
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    try:
        seq = list(value)
        if all(isinstance(x, (int, float, bool)) for x in seq):
            return seq
    except Exception:
        pass
    return None


def color_to_hex(color):
    try:
        vals = list(color)
        if len(vals) < 3:
            return ""
        r = max(0, min(255, round(vals[0] * 255)))
        g = max(0, min(255, round(vals[1] * 255)))
        b = max(0, min(255, round(vals[2] * 255)))
        a = max(0, min(255, round((vals[3] if len(vals) > 3 else 1.0) * 255)))
        return f"#{r:02X}{g:02X}{b:02X}{a:02X}"
    except Exception:
        return ""



def rgba_or_default(value):
    try:
        vals = list(value)
        if len(vals) >= 3:
            return (
                float(vals[0]),
                float(vals[1]),
                float(vals[2]),
                float(vals[3]) if len(vals) > 3 else 1.0,
            )
    except Exception:
        pass
    return (0.0, 0.0, 0.0, 1.0)


def collect_props(obj, include_all=False, keywords=KEYWORDS, limit=800):
    if obj is None:
        return {}
    out = {}
    rna = safe_get(obj, "bl_rna")
    props = safe_get(rna, "properties", [])
    kws = tuple(k.lower() for k in keywords)
    count = 0
    for prop in props:
        ident = getattr(prop, "identifier", "")
        if not ident or ident == "rna_type" or getattr(prop, "is_readonly", True):
            continue
        if not include_all and kws and not any(k in ident.lower() for k in kws):
            continue
        try:
            val = getattr(obj, ident)
        except Exception:
            continue
        val = to_json_value(val)
        if val is not None:
            out[ident] = val
            count += 1
        if count >= limit:
            break
    return out


def apply_props(obj, values):
    applied, skipped = 0, []
    if obj is None or not isinstance(values, dict):
        return applied, skipped
    blocked = {"name", "users", "use_fake_user", "asset_data", "rna_type"}
    for key, val in values.items():
        if key in blocked:
            skipped.append(key)
            continue
        if safe_set(obj, key, val):
            applied += 1
        else:
            skipped.append(key)
    return applied, skipped


def get_active_tool_id(context):
    try:
        tool = context.workspace.tools.from_space_view3d_mode(context.mode, create=False)
        return tool.idname if tool else ""
    except Exception:
        return ""


def set_active_tool(tool_id):
    if not tool_id:
        return False
    try:
        bpy.ops.wm.tool_set_by_id(name=tool_id)
        return True
    except Exception:
        return False


def brush_containers(context):
    ts = getattr(context, "tool_settings", None)
    if ts is None:
        return
    names = [
        "gpencil_paint", "grease_pencil_paint",
        "gpencil_sculpt_paint", "grease_pencil_sculpt_paint",
        "gpencil_vertex_paint", "grease_pencil_vertex_paint",
        "gpencil_weight_paint", "grease_pencil_weight_paint",
        "image_paint", "sculpt",
    ]
    seen = set()
    for name in names:
        obj = safe_get(ts, name)
        if obj is not None and hasattr(obj, "brush") and id(obj) not in seen:
            seen.add(id(obj))
            yield name, obj
    rna = safe_get(ts, "bl_rna")
    for prop in safe_get(rna, "properties", []):
        name = getattr(prop, "identifier", "")
        obj = safe_get(ts, name)
        if obj is not None and hasattr(obj, "brush") and id(obj) not in seen:
            seen.add(id(obj))
            yield name, obj


def active_brush(context):
    for preferred in ("gpencil_paint", "grease_pencil_paint"):
        obj = safe_get(context.tool_settings, preferred)
        brush = safe_get(obj, "brush")
        if brush is not None:
            return brush
    for name, obj in brush_containers(context):
        brush = safe_get(obj, "brush")
        if brush is not None:
            return brush
    return None


def assign_brush_to_containers(context, brush):
    ok = False
    for name, obj in brush_containers(context):
        if safe_set(obj, "brush", brush):
            ok = True
    try:
        context.view_layer.update()
    except Exception:
        pass
    return ok


def mark_asset_once(brush):
    # A single visible brush is intentional so users can return to it from the brush list.
    if brush is None:
        return False
    try:
        if brush.asset_data is None:
            brush.asset_mark()
        return True
    except Exception:
        return False


def activate_runtime_brush(brush):
    if brush is None:
        return False
    mark_asset_once(brush)
    for rel in (f"Brush/{brush.name}", brush.name):
        try:
            bpy.ops.brush.asset_activate(
                asset_library_type="LOCAL",
                asset_library_identifier="",
                relative_asset_identifier=rel,
            )
            return True
        except Exception:
            pass
    uid = safe_get(brush, "session_uid")
    if uid:
        try:
            bpy.ops.brush.asset_activate(
                asset_library_type="LOCAL",
                asset_library_identifier="",
                relative_asset_identifier="",
                session_uid=uid,
            )
            return True
        except Exception:
            pass
    return False


def ensure_runtime_brush(context, source_name=""):
    runtime = bpy.data.brushes.get(RUNTIME_BRUSH_NAME)
    if runtime:
        mark_asset_once(runtime)
        return runtime
    source = bpy.data.brushes.get(source_name) if source_name else None
    if source is None:
        source = active_brush(context)
    if source is not None:
        try:
            runtime = source.copy()
            runtime.name = RUNTIME_BRUSH_NAME
            runtime.use_fake_user = True
            mark_asset_once(runtime)
            return runtime
        except Exception:
            pass
    try:
        runtime = bpy.data.brushes.new(name=RUNTIME_BRUSH_NAME, mode="PAINT_GPENCIL")
        runtime.use_fake_user = True
        mark_asset_once(runtime)
        return runtime
    except Exception:
        return None


def set_active_brush(context, brush):
    if brush is None:
        return False
    assigned = assign_brush_to_containers(context, brush)
    activated = activate_runtime_brush(brush)
    assigned = assign_brush_to_containers(context, brush) or assigned
    return assigned or activated


def ensure_gp_mat(mat):
    if mat is None:
        return None
    gp = safe_get(mat, "grease_pencil")
    if gp is None:
        try:
            bpy.data.materials.create_gpencil_data(mat)
        except Exception:
            pass
    return safe_get(mat, "grease_pencil")


def capture_material_info(mat):
    if mat is None:
        return {"name": "", "stroke_hex": "", "fill_hex": ""}
    gp = ensure_gp_mat(mat)
    stroke_color = safe_get(gp, "color")
    fill_color = safe_get(gp, "fill_color")
    return {
        "name": mat.name,
        "stroke_color": to_json_value(stroke_color),
        "stroke_hex": color_to_hex(stroke_color),
        "fill_color": to_json_value(fill_color),
        "fill_hex": color_to_hex(fill_color),
        "show_stroke": safe_get(gp, "show_stroke"),
        "show_fill": safe_get(gp, "show_fill"),
    }


def set_active_existing_material(context, material_name):
    # Only switch to existing material. Never create, duplicate, delete, or edit materials.
    if not material_name:
        return False
    obj = getattr(context, "object", None)
    mat = bpy.data.materials.get(material_name)
    if obj is None or mat is None:
        return False
    try:
        for i, slot in enumerate(obj.material_slots):
            if slot.material == mat:
                obj.active_material_index = i
                return True
        obj.data.materials.append(mat)
        obj.active_material_index = len(obj.material_slots) - 1
        return True
    except Exception:
        return False


def capture_brush(brush):
    if brush is None:
        return {}
    important = {}
    for attr in IMPORTANT_BRUSH_ATTRS:
        val = to_json_value(safe_get(brush, attr))
        if val is not None:
            important[attr] = val
    gp = safe_get(brush, "gpencil_settings") or safe_get(brush, "grease_pencil_settings")
    return {
        "source_brush_name": brush.name,
        "runtime_brush_name": RUNTIME_BRUSH_NAME,
        "important": important,
        "brush_properties": collect_props(brush, include_all=True),
        "gpencil_settings": collect_props(gp, include_all=True),
    }


def restore_brush_to_runtime(context, brush_data):
    if not isinstance(brush_data, dict):
        return {"applied": 0, "skipped": ["brush"], "brush_name": ""}
    runtime = ensure_runtime_brush(context, brush_data.get("source_brush_name", ""))
    if runtime is None:
        return {"applied": 0, "skipped": ["runtime brush"], "brush_name": ""}
    applied, skipped = 0, []
    a, s = apply_props(runtime, brush_data.get("brush_properties", {}))
    applied += a; skipped += s
    a, s = apply_props(runtime, brush_data.get("important", {}))
    applied += a; skipped += s
    gp = safe_get(runtime, "gpencil_settings") or safe_get(runtime, "grease_pencil_settings")
    a, s = apply_props(gp, brush_data.get("gpencil_settings", {}))
    applied += a; skipped += [f"gpencil_settings.{x}" for x in s]
    if not set_active_brush(context, runtime):
        skipped.append("brush activation")
    return {"applied": applied, "skipped": skipped, "brush_name": runtime.name}


def capture_tool_settings(context):
    data = {}
    for name, obj in brush_containers(context):
        data[name] = collect_props(obj, include_all=False)
    return data


def restore_tool_settings(context, data):
    applied, skipped = 0, []
    if not isinstance(data, dict):
        return {"applied": applied, "skipped": skipped}
    for name, values in data.items():
        obj = safe_get(context.tool_settings, name)
        a, s = apply_props(obj, values)
        applied += a; skipped += [f"{name}.{x}" for x in s]
    return {"applied": applied, "skipped": skipped}


def capture_current_preset(context, name):
    brush = active_brush(context)
    mat = safe_get(getattr(context, "object", None), "active_material")
    material_info = capture_material_info(mat)
    return {
        "schema_version": SCHEMA_VERSION,
        "name": name,
        "blender_version_saved": ".".join(str(x) for x in bpy.app.version),
        "mode": getattr(context, "mode", ""),
        "tool_id": get_active_tool_id(context),
        "object_type": safe_get(getattr(context, "object", None), "type", ""),
        "material_name": material_info.get("name", ""),
        "material_info": material_info,
        "brush": capture_brush(brush),
        "tool_settings": capture_tool_settings(context),
    }


def apply_preset_data(context, data, prefs=None):
    if not isinstance(data, dict):
        return {"skipped": ["invalid preset"]}
    skipped = []
    set_active_tool(data.get("tool_id", ""))
    material_name = data.get("material_name") or data.get("material_info", {}).get("name", "")
    if material_name and not set_active_existing_material(context, material_name):
        skipped.append("material missing")
    brush_result = restore_brush_to_runtime(context, data.get("brush", {}))
    skipped += brush_result.get("skipped", [])
    ts_result = restore_tool_settings(context, data.get("tool_settings", {}))
    skipped += ts_result.get("skipped", [])
    runtime = bpy.data.brushes.get(RUNTIME_BRUSH_NAME)
    if runtime:
        set_active_brush(context, runtime)
    if prefs is not None:
        try:
            prefs.last_applied = data.get("name", "")
        except Exception:
            pass
    return {
        "brush_name": brush_result.get("brush_name", ""),
        "applied": brush_result.get("applied", 0) + ts_result.get("applied", 0),
        "skipped": skipped,
    }


def preset_summary(data):
    brush = data.get("brush", {}) if isinstance(data, dict) else {}
    important = brush.get("important", {})
    material = data.get("material_info", {}) if isinstance(data, dict) else {}
    return {
        "tool_id": data.get("tool_id", "") if isinstance(data, dict) else "",
        "source_brush": brush.get("source_brush_name", ""),
        "runtime_brush": RUNTIME_BRUSH_NAME,
        "material": material.get("name", ""),
        "stroke_color": rgba_or_default(material.get("stroke_color")),
        "fill_color": rgba_or_default(material.get("fill_color")),
        "stroke_hex": material.get("stroke_hex", ""),
        "fill_hex": material.get("fill_hex", ""),
        "size": important.get("size", "-"),
        "strength": important.get("strength", "-"),
        "hardness": important.get("hardness", "-"),
        "spacing": important.get("spacing", "-"),
        "stabilizer": important.get("use_smooth_stroke", "-"),
        "stabilizer_radius": important.get("smooth_stroke_radius", "-"),
        "stabilizer_factor": important.get("smooth_stroke_factor", "-"),
        "pressure_size": important.get("use_pressure_size", "-"),
        "pressure_strength": important.get("use_pressure_strength", "-"),
        "saved_in": data.get("blender_version_saved", "-") if isinstance(data, dict) else "-",
    }


def preset_to_json(data):
    return json.dumps(data, indent=2, sort_keys=True)


def preset_from_json(text):
    try:
        return json.loads(text or "{}")
    except Exception:
        return {}
