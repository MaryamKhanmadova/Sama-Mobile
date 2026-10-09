import bpy, sys, math
from mathutils import Vector
argv = sys.argv[sys.argv.index("--")+1:]
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=argv[0])
for o in list(bpy.context.scene.objects):
    if o.name.startswith(("MouthInterior","TeethUpper","Eyelids")): bpy.data.objects.remove(o)
body=[o for o in bpy.context.scene.objects if o.type=="MESH"][0]
me=body.data
print("polys",len(me.polygons),"verts",len(me.vertices))
# faces around the mouth: count normals pointing backwards (+Y) among front faces
import statistics
S,CZ=0.48976/1000,0.21578
mz=CZ-292*S
bad=[p for p in me.polygons if abs(p.center.x)<0.06 and abs(p.center.z-mz)<0.03 and p.center.y<-0.18]
back=[p for p in bad if p.normal.y>0.2]
print("mouth faces",len(bad),"backfacing",len(back))
cam=bpy.data.objects.new("cam",bpy.data.cameras.new("cam")); bpy.context.scene.collection.objects.link(cam)
cam.data.type="ORTHO"; cam.data.ortho_scale=0.16; cam.location=Vector((0,-1.5,mz)); cam.rotation_euler=(math.radians(90),0,0); bpy.context.scene.camera=cam
l=bpy.data.objects.new("l",bpy.data.lights.new("l","SUN")); l.data.energy=4; l.rotation_euler=(math.radians(70),0,0); bpy.context.scene.collection.objects.link(l)
s=bpy.context.scene; s.render.resolution_x=s.render.resolution_y=500; s.render.filepath=argv[1]
bpy.ops.render.render(write_still=True)
