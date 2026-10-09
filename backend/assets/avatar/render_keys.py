import bpy, sys, math, json
from mathutils import Vector
argv = sys.argv[sys.argv.index("--")+1:]
src, outdir = argv[0], argv[1]
poses = json.loads(argv[2])
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=src)
S, CZ = 0.48976/1000, 0.21578
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam")); bpy.context.scene.collection.objects.link(cam)
cam.data.type = "ORTHO"; cam.data.ortho_scale = float(argv[3]) if len(argv) > 3 else 0.30
cam.location = Vector((0, -1.5, CZ - 0.06)); cam.rotation_euler = (math.radians(90), 0, 0); bpy.context.scene.camera = cam
for loc,e in [((-1,-2,1),500),((1.5,-2,0.5),300)]:
    l=bpy.data.objects.new("l",bpy.data.lights.new("l","AREA")); l.data.energy=e; l.data.size=2; l.location=Vector(loc)+Vector((0,0,CZ)); bpy.context.scene.collection.objects.link(l)
    l.rotation_euler=(Vector((0,0,CZ))-l.location).to_track_quat("-Z","Y").to_euler()
w=bpy.data.worlds.new("w"); bpy.context.scene.world=w; w.use_nodes=True; w.node_tree.nodes["Background"].inputs[1].default_value=0.8
s=bpy.context.scene; s.render.resolution_x=s.render.resolution_y=500
meshes=[o for o in s.objects if o.type=="MESH" and o.data.shape_keys]
for name, vals in poses.items():
    for o in meshes:
        for kb in o.data.shape_keys.key_blocks[1:]: kb.value = vals.get(kb.name, 0.0)
    # jaw drives nothing else in Blender; the app moves MouthInterior/Teeth if needed
    yaw, pitch = vals.get("_eyes", [0, 0])
    for ob in s.objects:
        if ob.name.startswith("Eye") and ob.name != "Eyelids":
            ob.rotation_mode = "XYZ"; ob.rotation_euler = (math.radians(pitch), 0, math.radians(yaw))
    s.render.filepath = f"{outdir}/k_{name}.png"; bpy.ops.render.render(write_still=True)
print("OK", list(poses))
