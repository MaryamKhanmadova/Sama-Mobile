import bpy, sys, math, json
from mathutils import Vector
argv = sys.argv[sys.argv.index("--")+1:]
src, out = argv[0], argv[1]
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=src)
o = [x for x in bpy.context.scene.objects if x.type == "MESH"][0]
bpy.context.view_layer.objects.active = o; o.select_set(True)
o.rotation_mode = "XYZ"; o.rotation_euler = (0, 0, math.radians(-90))  # face +X -> -Y (front)
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
vs = [o.matrix_world @ v.co for v in o.data.vertices]
xs=[v.x for v in vs]; ys=[v.y for v in vs]; zs=[v.z for v in vs]
info = {"xmin":min(xs),"xmax":max(xs),"ymin":min(ys),"ymax":max(ys),"zmin":min(zs),"zmax":max(zs)}
# head region: upper 45% of height
zc = info["zmin"] + (info["zmax"]-info["zmin"])*0.72; half = (info["zmax"]-info["zmin"])*0.25
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam")); bpy.context.scene.collection.objects.link(cam)
cam.data.type = "ORTHO"; cam.data.ortho_scale = half*2
cam.location = Vector((0, info["ymin"]-1.0, zc)); cam.rotation_euler = (math.radians(90),0,0)
bpy.context.scene.camera = cam
for loc,e in [((-1,-2,1),500),((1.5,-2,0.5),300)]:
    l=bpy.data.objects.new("l",bpy.data.lights.new("l","AREA")); l.data.energy=e; l.data.size=2; l.location=Vector(loc)+Vector((0,0,zc)); bpy.context.scene.collection.objects.link(l)
    l.rotation_euler=(Vector((0,0,zc))-l.location).to_track_quat("-Z","Y").to_euler()
w=bpy.data.worlds.new("w"); bpy.context.scene.world=w; w.use_nodes=True; w.node_tree.nodes["Background"].inputs[1].default_value=0.8
s=bpy.context.scene; s.render.resolution_x=s.render.resolution_y=1000; s.render.filepath=out
bpy.ops.render.render(write_still=True)
info.update({"cam_x":0.0,"cam_z":zc,"ortho":half*2,"px":1000})
json.dump(info, open(out.replace(".png",".json"),"w"))
print("OK", info)
