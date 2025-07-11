import bpy
from pathlib import Path
import sys
import importlib
import numpy as np
import mathutils
# sys.path.append(str(Path(__file__).parent))
#### Set Path to repo/blender_integration here ####
sys.path.append(r"D:\Projects\Head_Neck_Marker_Alignment\code_base\visual_guidance\blender_integration")
import texture_transfer_op as tto
import ModelAlignerV5 as ma
importlib.reload(tto)
importlib.reload(ma)

##### OPERATION MODE #####
RUN_MODE = "SURFACE_ONLY" # FULL

##### Variables and CONFIGS ####
# Surface Related
surf_name = "PC"
bedFidsPath = Path(r"D:\Projects\Head_Neck_Marker_Alignment\data\EXP\20250206_run\run2\0024_cav\frame0010_fids.vtk")

# Specimen Mesh/Deformed Model Related
scan_name = "scan_model"
bel_name = "bel"
deformed_bel_name = "bel_deformed"
deformedFidsPath = Path(r"D:\Projects\Head_Neck_Marker_Alignment\data\EXP\20250206_run\run2\Deformed\0024_fids_mm_Deformed.vtk")
undeformedFidsPath = Path(r"D:\Projects\Head_Neck_Marker_Alignment\data\EXP\20250206_run\run2\Deformed\0024_fids.vtk")

# Target Related
targ_obj_name = "target"
targPath = Path(r"D:\Projects\Head_Neck_Marker_Alignment\data\EXP\20250206_run\run2\Deformed\0024_tgt_mm_Deformed.vtk") # None







##### Create Target Marker Object #####
if targ_obj_name not in bpy.data.objects:
    # Create Target
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.0015, location=(0, 0, 0))
    sphere = bpy.context.active_object
    sphere.name = targ_obj_name

    green_metal = bpy.data.materials.new(name="GreenMetal")
    green_metal.use_nodes = True
    nodes = green_metal.node_tree.nodes
    bsdf = nodes.get("Principled BSDF")

    if bsdf:
        # Set Base Color to green (R, G, B, A)
        bsdf.inputs["Base Color"].default_value = (0.0, 1.0, 0.0, 1)
        # Set Metallic to 1 for a metallic appearance
        bsdf.inputs["Metallic"].default_value = 1.0
        # Optionally, adjust roughness for a shinier finish
        bsdf.inputs["Roughness"].default_value = 0.2

    if sphere.data.materials:
        sphere.data.materials[0] = green_metal
    else:
        sphere.data.materials.append(green_metal)

# Registration and Texture Transfer
model_names = [scan_name, bel_name, deformed_bel_name]
if not (surf_name in bpy.data.objects):
    print("ERROR! surface name provided not found in scene object list! Surface Registration Not Performed! Did you forget to rename the point cloud?")
else: 
    #if False in [cur_name in bpy.data.objects for cur_name in model_names]:
    if RUN_MODE.upper() == "SURFACE_ONLY": # Surface Registration
        # Models not loaded yet, just register the surface
        print("WARNING: specimen files not found, skipping their registration and texture transfer")
        surf_pc = bpy.data.objects[surf_name]

        print("Performing Surface PC Registration")
        outputTs = ma.main(bedFidsPath=bedFidsPath,specimenFidsPath=None,undeformedFidsPath=None,targPath=None)
        ma.transform_obj(surf_pc, *(outputTs["aruco_T_bed"])) # target_in_aruco
    elif RUN_MODE.upper() == "FULL": # Deformed Model Regstration and Texture Transfer
        print("All specimen files specified, performing specimen to Aruco Registration and texture transfer")
        surf_pc = bpy.data.objects[surf_name]
        obj_scan = bpy.data.objects[scan_name]
        obj_bel = bpy.data.objects[bel_name]
        obj_bel_deformed = bpy.data.objects[deformed_bel_name]
        
        print("Performing Texture Transfer First")
        tto.main(obj_scan, obj_bel, obj_bel_deformed, obj_bel_transfer_modeifiers=['NEAREST_POLYNOR', 'NEAREST'], obj_deformed_transfer_modifiers=["TOPOLOGY", "TOPOLOGY"])

        print("Performing Specimen Model Registrations")
        outputTs = ma.main(bedFidsPath=bedFidsPath,specimenFidsPath=deformedFidsPath,undeformedFidsPath=undeformedFidsPath,targPath=targPath)
        # transform_obj(obj_bel, *(outputTs["aruco_T_undeformed"])) 
        ma.transform_obj(obj_bel_deformed, *(outputTs["aruco_T_deformed"])) 
        ma.transform_obj(surf_pc, *(outputTs["aruco_T_bed"])) 
        if not targPath is None:
            assert(targ_obj_name in bpy.data.objects)
            print("Positioning targetPath")
            targ_obj = bpy.data.objects[targ_obj_name]
            ma.transform_obj(targ_obj, [0, 0, 0], outputTs["target_in_aruco"])
            
