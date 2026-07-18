# SPDX-License-Identifier: MIT

import json
import bpy

SCHEMA_VERSION = 11
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
    "curve", "falloff", "active_smooth", "solver", "delaunay",
    "precision", "invert", "boundary", "extension", "closure",
    "threshold", "leak", "mode", "layer", "guide", "limit",
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


def _valid_color(value):
    try:
        values = list(value)
        return len(values) >= 3 and all(isinstance(v, (int, float)) for v in values[:3])
    except Exception:
        return False


def _first_color(candidates):
    for source_path, obj, attr in candidates:
        value = safe_get(obj, attr)
        if _valid_color(value):
            return value, source_path
    return None, ""


def get_gp_paint_container(context):
    ts = safe_get(context, "tool_settings")
    for name in ("gpencil_paint", "grease_pencil_paint"):
        container = safe_get(ts, name)
        if container is not None:
            return name, container
    for name, container in brush_containers(context):
        if "gpencil" in name.lower() or "grease_pencil" in name.lower():
            return name, container
    return "", None


def detect_color_mode(context):
    """Detect whether the GP tool uses Material or Color Attribute color."""
    container_name, paint = get_gp_paint_container(context)
    raw = safe_get(paint, "color_mode", "")
    raw_text = str(raw or "").upper()
    if raw_text in {"VERTEXCOLOR", "COLOR_ATTRIBUTE", "VERTEX_COLOR"}:
        return "COLOR_ATTRIBUTE", raw_text, container_name
    if raw_text:
        return "MATERIAL", raw_text, container_name
    return "MATERIAL", "", container_name


def capture_color_info(context, mat, brush):
    color_source, raw_mode, container_name = detect_color_mode(context)
    gp = ensure_gp_mat(mat) if mat is not None else None
    gp_brush = safe_get(brush, "gpencil_settings") or safe_get(brush, "grease_pencil_settings")
    _, paint = get_gp_paint_container(context)

    if color_source == "COLOR_ATTRIBUTE":
        stroke_color, stroke_path = _first_color((
            ("brush.color", brush, "color"),
            ("gpencil_settings.color", gp_brush, "color"),
            ("paint.color", paint, "color"),
            ("brush.primary_color", brush, "primary_color"),
        ))
        fill_color, fill_path = _first_color((
            ("brush.secondary_color", brush, "secondary_color"),
            ("gpencil_settings.fill_color", gp_brush, "fill_color"),
            ("paint.secondary_color", paint, "secondary_color"),
            ("paint.fill_color", paint, "fill_color"),
        ))
    else:
        stroke_color, stroke_path = _first_color((
            ("material.grease_pencil.color", gp, "color"),
            ("material.diffuse_color", mat, "diffuse_color"),
        ))
        fill_color, fill_path = _first_color((
            ("material.grease_pencil.fill_color", gp, "fill_color"),
        ))

    return {
        "name": mat.name if mat else "",
        "color_source": color_source,
        "color_mode_raw": raw_mode,
        "paint_container": container_name,
        "stroke_color": to_json_value(stroke_color),
        "stroke_hex": color_to_hex(stroke_color),
        "stroke_source_path": stroke_path,
        "fill_color": to_json_value(fill_color),
        "fill_hex": color_to_hex(fill_color),
        "fill_source_path": fill_path,
        "show_stroke": safe_get(gp, "show_stroke"),
        "show_fill": safe_get(gp, "show_fill"),
    }


def apply_saved_color_mode(context, material_info, runtime_brush):
    """Restore Color Attribute values without changing material data."""
    if not isinstance(material_info, dict):
        return {"applied": 0, "skipped": []}

    source = material_info.get("color_source", "MATERIAL")
    _, paint = get_gp_paint_container(context)
    applied, skipped = 0, []

    if paint is not None and hasattr(paint, "color_mode"):
        target_mode = "VERTEXCOLOR" if source == "COLOR_ATTRIBUTE" else "MATERIAL"
        if safe_set(paint, "color_mode", target_mode):
            applied += 1
        else:
            skipped.append("color_mode")

    if source != "COLOR_ATTRIBUTE" or runtime_brush is None:
        return {"applied": applied, "skipped": skipped}

    gp_brush = safe_get(runtime_brush, "gpencil_settings") or safe_get(
        runtime_brush, "grease_pencil_settings"
    )
    stroke = material_info.get("stroke_color")
    fill = material_info.get("fill_color")

    if stroke is not None:
        restored = False
        for obj, attr in ((runtime_brush, "color"), (gp_brush, "color")):
            if obj is not None and safe_set(obj, attr, stroke):
                restored = True
                break
        applied += int(restored)
        if not restored:
            skipped.append("stroke color attribute")

    if fill is not None:
        restored = False
        for obj, attr in ((runtime_brush, "secondary_color"), (gp_brush, "fill_color")):
            if obj is not None and safe_set(obj, attr, fill):
                restored = True
                break
        applied += int(restored)
        if not restored:
            skipped.append("fill color attribute")

    return {"applied": applied, "skipped": skipped}


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



FILL_OPERATOR_IDS = (
    "grease_pencil.fill",
    "grease_pencil.fill_between_strokes",
)

FILL_SETTING_KEYWORDS = (
    "fill", "gap", "solver", "delaunay", "precision", "invert",
    "boundary", "extension", "extend", "closure", "threshold",
    "leak", "layer", "guide", "limit", "radius", "factor",
)


def _rna_pointer_children(obj):
    """Yield writable/readable RNA pointer children without recursing indefinitely."""
    if obj is None:
        return
    rna = safe_get(obj, "bl_rna")
    for prop in safe_get(rna, "properties", []):
        ident = getattr(prop, "identifier", "")
        if not ident or ident == "rna_type":
            continue
        if getattr(prop, "type", "") != "POINTER":
            continue
        child = safe_get(obj, ident)
        if child is not None and safe_get(child, "bl_rna") is not None:
            yield ident, child


def capture_fill_settings(context):
    """Capture Fill-related values exposed by Blender 5.1/5.2.

    This is capability-based rather than version-based. Blender 5.1 simply
    stores fewer values; Blender 5.2 can contribute the new solver/gap values.
    """
    result = {"tool_settings": {}, "nested": {}, "operator_properties": {}}
    ts = safe_get(context, "tool_settings")
    if ts is not None:
        result["tool_settings"] = collect_props(
            ts, include_all=False, keywords=FILL_SETTING_KEYWORDS, limit=400
        )
        for child_name, child in _rna_pointer_children(ts):
            name_low = child_name.lower()
            child_values = collect_props(
                child, include_all=False, keywords=FILL_SETTING_KEYWORDS, limit=400
            )
            if child_values and (
                any(k in name_low for k in ("grease", "gpencil", "paint", "fill"))
                or any(any(k in prop.lower() for k in FILL_SETTING_KEYWORDS) for prop in child_values)
            ):
                result["nested"][child_name] = child_values

    try:
        tool = context.workspace.tools.from_space_view3d_mode(context.mode, create=False)
    except Exception:
        tool = None
    if tool is not None:
        for op_id in FILL_OPERATOR_IDS:
            try:
                props = tool.operator_properties(op_id)
            except Exception:
                continue
            values = collect_props(props, include_all=True, limit=400)
            if values:
                result["operator_properties"][op_id] = values

    if not any(result.values()):
        return {}
    return result


def apply_fill_settings(context, data):
    applied, skipped = 0, []
    if not isinstance(data, dict):
        return {"applied": 0, "skipped": []}

    ts = safe_get(context, "tool_settings")
    a, s = apply_props(ts, data.get("tool_settings", {}))
    applied += a
    skipped += [f"tool_settings.{x}" for x in s]

    for child_name, values in data.get("nested", {}).items():
        child = safe_get(ts, child_name)
        a, s = apply_props(child, values)
        applied += a
        skipped += [f"{child_name}.{x}" for x in s]

    try:
        tool = context.workspace.tools.from_space_view3d_mode(context.mode, create=False)
    except Exception:
        tool = None
    if tool is not None:
        for op_id, values in data.get("operator_properties", {}).items():
            try:
                props = tool.operator_properties(op_id)
            except Exception:
                skipped.append(f"{op_id} unavailable")
                continue
            a, s = apply_props(props, values)
            applied += a
            skipped += [f"{op_id}.{x}" for x in s]

    return {"applied": applied, "skipped": skipped}


def fill_settings_summary(data):
    fill = data.get("fill_settings", {}) if isinstance(data, dict) else {}
    flat = {}
    for section in ("tool_settings",):
        flat.update(fill.get(section, {}))
    for child, values in fill.get("nested", {}).items():
        for key, value in values.items():
            flat[f"{child}.{key}"] = value
    for op_id, values in fill.get("operator_properties", {}).items():
        for key, value in values.items():
            flat[f"{op_id}.{key}"] = value

    preferred = {}
    for label, needles in (
        ("Solver", ("solver", "algorithm", "delaunay")),
        ("Gap Closure", ("gap", "closure")),
        ("Precision", ("precision",)),
        ("Invert", ("invert",)),
        ("Extension", ("extend", "extension")),
    ):
        for key, value in flat.items():
            if any(n in key.lower() for n in needles):
                preferred[label] = value
                break
    return {"count": len(flat), "preferred": preferred}


def capture_current_preset(context, name):
    brush = active_brush(context)
    mat = safe_get(getattr(context, "object", None), "active_material")
    material_info = capture_color_info(context, mat, brush)
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
        "fill_settings": capture_fill_settings(context),
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

    runtime = bpy.data.brushes.get(RUNTIME_BRUSH_NAME)
    color_result = apply_saved_color_mode(
        context, data.get("material_info", {}), runtime
    )
    skipped += color_result.get("skipped", [])

    ts_result = restore_tool_settings(context, data.get("tool_settings", {}))
    skipped += ts_result.get("skipped", [])
    fill_result = apply_fill_settings(context, data.get("fill_settings", {}))
    skipped += fill_result.get("skipped", [])
    if runtime:
        set_active_brush(context, runtime)
    if prefs is not None:
        try:
            prefs.last_applied = data.get("name", "")
        except Exception:
            pass
    return {
        "brush_name": brush_result.get("brush_name", ""),
        "applied": (brush_result.get("applied", 0) + ts_result.get("applied", 0)
                    + fill_result.get("applied", 0) + color_result.get("applied", 0)),
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
        "color_source": material.get("color_source", "MATERIAL"),
        "color_mode_raw": material.get("color_mode_raw", ""),
        "stroke_source_path": material.get("stroke_source_path", ""),
        "fill_source_path": material.get("fill_source_path", ""),
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
