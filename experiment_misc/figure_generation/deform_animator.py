from pathlib import Path
import argparse
import sys

from scipy.spatial.transform import Rotation as R
import numpy as np
import vtk
from vtk.util.numpy_support import numpy_to_vtk, vtk_to_numpy
import time

sys.path.append("../../visual_guidance/blender_integration")
from utils import loadMeshFile, loadMeshFileAndWriteAsPLY

if __name__ == "__main__":
    bel_path = Path(r"d:\Projects\Head_Neck_Marker_Alignment\data\miccai_2025_data\0013_bel.vtk")
    bel_deformed_path = Path(r"d:\Projects\Head_Neck_Marker_Alignment\data\miccai_2025_data\0013_bel_deformed_initial.vtk")
    
    bel_mesh = loadMeshFile(bel_path)
    bel_deformed_mesh = loadMeshFile(bel_deformed_path)

    copy_mesh = vtk.vtkPolyData()
    copy_mesh.DeepCopy(bel_mesh)

    displacement_field_path = Path(r"d:\Projects\Head_Neck_Marker_Alignment\data\miccai_2025_data\0013_displacement.out")
    displacements = np.genfromtxt(displacement_field_path, delimiter=" ")

    tgt_path = Path(r"d:\Projects\Head_Neck_Marker_Alignment\data\miccai_2025_data\0013_tgt.vtk")
    tgt_pts = loadMeshFile(tgt_path)
    
    tgt_displacement_path = Path(r"d:\Projects\Head_Neck_Marker_Alignment\data\miccai_2025_data\1013_tgt_transformed.vtk")
    tgt_displacement_pts = loadMeshFile(tgt_displacement_path)

    print(displacements.shape)

    mapper = vtk.vtkPolyDataMapper()
    mapper.SetInputData(copy_mesh)
    actor = vtk.vtkActor()
    actor.SetMapper(mapper)
    ren = vtk.vtkRenderer()
    ren.AddActor(actor)
    win = vtk.vtkRenderWindow()
    win.AddRenderer(ren)
    win.SetSize(1080, 1080)
    iren = vtk.vtkRenderWindowInteractor()
    iren.SetRenderWindow(win)

    iren.Initialize()
    win.Render()  # show the first frame

    print(tgt_displacement_pts)
    print(tgt_pts)

    alphas = np.linspace(0.0, 1.0, 50)
    for alpha in alphas:
        print(alpha)
        old_points = vtk_to_numpy(bel_mesh.GetPoints().GetData()).copy()
        final_points = vtk_to_numpy(bel_deformed_mesh.GetPoints().GetData()).copy()
        new_points = (1 - alpha) * old_points + final_points * alpha # displacements[:, 1:] * alpha
        vtk_new_points = vtk.vtkPoints()
        vtk_new_points.SetData(numpy_to_vtk(new_points))
        copy_mesh.SetPoints(vtk_new_points)
        copy_mesh.Modified()

        old_tgt_pts = vtk_to_numpy(tgt_pts.GetPoints().GetData()).copy()
        final_tgt_pts = vtk_to_numpy(tgt_displacement_pts.GetPoints().GetData()).copy()
        cur_tgt_pts = (1 - alpha) * old_tgt_pts + alpha * final_points 
        vtk_new_tgt = vtk.vtkPoints()
        vtk_new_tgt.SetData(numpy_to_vtk(cur_tgt_pts))
        
        
        win.Render()
        iren.ProcessEvents()
        time.sleep(0.5)

