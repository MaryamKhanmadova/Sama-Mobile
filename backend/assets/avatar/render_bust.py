import bpy, sys, math, json
from mathutils import Vector
argv = sys.argv[sys.argv.index("--")+1:]
src, outdir, poses = argv[0], argv[1], json.loads(argv[2])
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=src)
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam")); bpy.context.scene.collection.objects.link(cam)
cam.data.lens = 85; cam.location = Vector((0, -2.6, 0.17)); cam.rotation_euler = (math.radians(90), 0, 0); bpy.context.scene.camera = cam
for loc,e in [((-1.2,-2,1.2),700),((1.5,-1.8,0.4),350),((0,1.5,1.5),300)]:
    l=bpy.data.objects.new("l",bpy.data.lights.new("l","AREA")); l.data.energy=e; l.data.size=2.5; l.location=Vector(loc); bpy.context.scene.collection.objects.link(l)
    l.rotation_euler=(Vector((0,0,0.15))-l.location).to_track_quat("-Z","Y").to_euler()
w=bpy.data.worlds.new("w"); bpy.context.scene.world=w; w.use_nodes=True; w.node_tree.nodes["Background"].inputs[0].default_value=(0.93,0.91,0.97,1); w.node_tree.nodes["Background"].inputs[1].default_value=0.7
s=bpy.context.scene; s.render.resolution_x=s.render.resolution_y=512
meshes=[o for o in s.objects if o.type=="MESH" and o.data.shape_keys]
for name, vals in poses.items():
    for o in meshes:
        for kb in o.data.shape_keys.key_blocks[1:]: kb.value = vals.get(kb.name, 0.0)
    s.render.filepath = f"{outdir}/b_{name}.png"; bpy.ops.render.render(write_still=True)
print("OK")
