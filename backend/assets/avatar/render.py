import bpy, sys, math
from mathutils import Vector
argv = sys.argv[sys.argv.index("--")+1:]
src, out, zoom = argv[0], argv[1], float(argv[2]) if len(argv) > 2 else 1.0
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=src)
objs = [o for o in bpy.context.scene.objects if o.type == "MESH"]
pts = [o.matrix_world @ Vector(c) for o in objs for c in o.bound_box]
mn = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
mx = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
c = (mn + mx) / 2; h = mx.z - mn.z
target = Vector((c.x, c.y, mn.z + h * (0.72 if zoom > 1 else 0.5)))
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam")); bpy.context.scene.collection.objects.link(cam)
cam.data.lens = 50 * zoom
# glTF +Z forward -> Blender -Y forward: camera in front (negative Y)
cam.location = target + Vector((h * 2.4, 0, 0)); cam.rotation_euler = (math.radians(90), 0, math.radians(90))
bpy.context.scene.camera = cam
for loc, e in [((2.5, -1.5, 2.0), 600), ((2.0, 2.0, 1.0), 300), ((-2, 0, 2), 200)]:
    l = bpy.data.objects.new("l", bpy.data.lights.new("l", "AREA")); l.data.energy = e; l.data.size = 3
    l.location = target + Vector(loc) * h; bpy.context.scene.collection.objects.link(l)
    l.rotation_euler = (target - l.location).to_track_quat("-Z", "Y").to_euler()
w = bpy.data.worlds.new("w"); bpy.context.scene.world = w; w.use_nodes = True
w.node_tree.nodes["Background"].inputs[0].default_value = (0.92, 0.91, 0.95, 1); w.node_tree.nodes["Background"].inputs[1].default_value = 0.6
s = bpy.context.scene; s.render.engine = "BLENDER_EEVEE_NEXT" if "BLENDER_EEVEE_NEXT" in [e.identifier for e in bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items] else "BLENDER_EEVEE"
s.render.resolution_x = s.render.resolution_y = 768; s.render.filepath = out
bpy.ops.render.render(write_still=True)
print("RENDERED", out, "tris", sum(len(o.data.polygons) for o in objs))
