import bpy, sys, math
from mathutils import Vector
argv = sys.argv[sys.argv.index("--")+1:]
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=argv[0])
body=[o for o in bpy.context.scene.objects if o.type=="MESH"][0]
body.rotation_mode="XYZ"; body.rotation_euler=(0,0,math.radians(-90))
bpy.context.view_layer.objects.active=body; body.select_set(True); bpy.ops.object.transform_apply(rotation=True)
S,CZ=0.48976/1000,0.21578; mz=CZ-292*S
# cross-section of the mouth at x=0: list surface y along z
me=body.data
pts=sorted([(round(v.co.z,4),round(v.co.y,4)) for v in me.vertices if abs(v.co.x)<0.0025 and abs(v.co.z-mz)<0.02 and v.co.y<-0.15])
print("x=0 section (z,y):",pts[:60])
cam=bpy.data.objects.new("cam",bpy.data.cameras.new("cam")); bpy.context.scene.collection.objects.link(cam)
cam.data.type="ORTHO"; cam.data.ortho_scale=0.16; cam.location=Vector((0,-1.5,mz)); cam.rotation_euler=(math.radians(90),0,0); bpy.context.scene.camera=cam
l=bpy.data.objects.new("l",bpy.data.lights.new("l","SUN")); l.data.energy=4; l.rotation_euler=(math.radians(70),0,0); bpy.context.scene.collection.objects.link(l)
s=bpy.context.scene; s.render.resolution_x=s.render.resolution_y=500; s.render.filepath=argv[1]
bpy.ops.render.render(write_still=True)
