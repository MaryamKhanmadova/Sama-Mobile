import bpy, bmesh, sys, math
from mathutils import Vector
argv = sys.argv[sys.argv.index("--")+1:]
src, ratio, weld, out = argv[0], float(argv[1]), argv[2] == "1", argv[3]
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=src)
b=[o for o in bpy.context.scene.objects if o.type=="MESH"][0]
bpy.context.view_layer.objects.active=b; b.select_set(True)
b.rotation_mode="XYZ"; b.rotation_euler=(0,0,math.radians(-90)); bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
if weld:
    bm=bmesh.new(); bm.from_mesh(b.data); bmesh.ops.remove_doubles(bm,verts=bm.verts,dist=1e-6); bm.to_mesh(b.data); bm.free()
if ratio < 1:
    m=b.modifiers.new("d","DECIMATE"); m.ratio=ratio; m.use_collapse_triangulate=True; bpy.ops.object.modifier_apply(modifier="d")
bpy.ops.object.shade_smooth()
S,CZ=0.48976/1000,0.21578; mz=CZ-292*S
cam=bpy.data.objects.new("cam",bpy.data.cameras.new("cam")); bpy.context.scene.collection.objects.link(cam)
cam.data.type="ORTHO"; cam.data.ortho_scale=0.16; cam.location=Vector((0,-1.5,mz)); cam.rotation_euler=(math.radians(90),0,0); bpy.context.scene.camera=cam
l=bpy.data.objects.new("l",bpy.data.lights.new("l","SUN")); l.data.energy=4; l.rotation_euler=(math.radians(70),0,0); bpy.context.scene.collection.objects.link(l)
s=bpy.context.scene; s.render.resolution_x=s.render.resolution_y=400; s.render.filepath=out
bpy.ops.render.render(write_still=True); print("OK",ratio,weld,len(b.data.polygons))
