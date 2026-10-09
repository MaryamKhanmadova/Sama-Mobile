import bpy, sys, math
from mathutils import Vector
argv = sys.argv[sys.argv.index("--")+1:]
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=argv[0])
o=[x for x in bpy.context.scene.objects if x.type=="MESH"][0]
bpy.context.view_layer.objects.active=o; o.select_set(True)
o.rotation_mode="XYZ"; o.rotation_euler=(0,0,math.radians(-90)); bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
S,CZ=0.48976/1000,0.21578
cam=bpy.data.objects.new("cam",bpy.data.cameras.new("cam")); bpy.context.scene.collection.objects.link(cam)
cam.data.type="ORTHO"; cam.data.ortho_scale=0.05; cam.rotation_euler=(math.radians(90),0,0); bpy.context.scene.camera=cam
w=bpy.data.worlds.new("w"); bpy.context.scene.world=w; w.use_nodes=True; w.node_tree.nodes["Background"].inputs[1].default_value=1.0
s=bpy.context.scene; s.render.resolution_x=s.render.resolution_y=600; s.view_settings.view_transform="Standard"
for name,px in [("L",(350,503)),("R",(656,503))]:
    x=(px[0]-500)*S; z=CZ-(px[1]-500)*S
    cam.location=Vector((x,-1.0,z)); s.render.filepath=f"{argv[1]}/eyecrop_{name}.png"; bpy.ops.render.render(write_still=True)
print("OK")
