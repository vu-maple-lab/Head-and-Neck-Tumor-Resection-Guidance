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

def get_lerped_pts_polydata(init_polydata:vtk.vtkPolyData, fin_polydata:vtk.vtkPolyData, alpha:float, output_polydata=None):
    np_lerped_pts = get_lerped_pts_vtk(init_polydata.GetPoints(), fin_polydata.GetPoints(), alpha)
    if output_polydata is None:
        output_polydata = vtk.vtkPolyData()
        output_polydata.DeepCopy(init_polydata)
    vtk_new_points = vtk.vtkPoints()
    vtk_new_points.SetData(numpy_to_vtk(np_lerped_pts))
    output_polydata.SetPoints(vtk_new_points)
    return output_polydata
    

def get_lerped_pts_vtk(init_vtk_points, fin_vtk_points, alpha):
    init_points = vtk_to_numpy(init_vtk_points.GetData()).copy()
    fin_points = vtk_to_numpy(fin_vtk_points.GetData()).copy()
    return get_lerped_pts(init_points, fin_points, alpha)

def get_lerped_pts(init_points, fin_points, alpha):
    return (1 - alpha) * init_points + alpha * fin_points 

class TimerCB:
    def __init__(
            self, 
            og_mesh: vtk.vtkPolyData, 
            deformed_mesh: vtk.vtkPolyData, 
            og_tgt: vtk.vtkPolyData,
            deformed_tgt: vtk.vtkPolyData,
            og_fids: vtk.vtkPolyData,
            deformed_fids: vtk.vtkPolyData
            ):
        self.t = 0
        self.t0 = 50
        self.nFrame = 100

        self.og_mesh = og_mesh
        self.deformed_mesh = deformed_mesh
        self.anim_mesh = vtk.vtkPolyData()
        self.anim_mesh.DeepCopy(self.og_mesh)
        self.anim_mesh_points = self.anim_mesh.GetPoints()

        self.og_tgt = og_tgt
        self.deformed_tgt = deformed_tgt
        self.anim_tgt = vtk.vtkPolyData()
        self.anim_tgt.DeepCopy(self.og_tgt)

        self.og_fids = og_fids
        self.deformed_fids = deformed_fids
        self.anim_fids = vtk.vtkPolyData()
        self.anim_fids.DeepCopy(self.og_fids)

        self.alphas = np.linspace(0.0, 1.0, self.nFrame)



    def execute(self, obj, event):
        # UPDATE YOUR POINTS HERE (example: oscillate x)
        if self.t < self.t0:
            self.t += 1
            return
        t_actual = self.t - self.t0
        if t_actual >= self.nFrame:
            obj.DestroyTimer(self.timer_id)
            print("Stop Here")
            return

        # for alpha in alphas:
        alpha = self.alphas[t_actual]

        get_lerped_pts_polydata(
            self.og_mesh, 
            self.deformed_mesh, 
            alpha=alpha, 
            output_polydata=self.anim_mesh
        )
        self.anim_mesh.Modified()

        get_lerped_pts_polydata(
            self.og_tgt, 
            self.deformed_tgt, 
            alpha=alpha, 
            output_polydata=self.anim_tgt
        )
        self.anim_tgt.Modified()

        get_lerped_pts_polydata(
            self.og_fids, 
            self.deformed_fids, 
            alpha=alpha, 
            output_polydata=self.anim_fids
        )
        self.anim_fids.Modified()
        win.Render()

        self.t += 1



if __name__ == "__main__":

    #------------------------------- Specimen Data -------------------------------#
    bel_path = Path(r"d:\Projects\Head_Neck_Marker_Alignment\data\miccai_2025_data\0013_bel.vtk")
    bel_deformed_path = Path(r"d:\Projects\Head_Neck_Marker_Alignment\data\miccai_2025_data\0013_bel_deformed_initial.vtk")
    
    bel_mesh = loadMeshFile(bel_path)
    bel_deformed_mesh = loadMeshFile(bel_deformed_path)

    displacement_field_path = Path(r"d:\Projects\Head_Neck_Marker_Alignment\data\miccai_2025_data\0013_displacement.out")
    displacements = np.genfromtxt(displacement_field_path, delimiter=" ")

    tgt_path = Path(r"d:\Projects\Head_Neck_Marker_Alignment\data\miccai_2025_data\0013_tgt.vtk")
    tgt_pts = loadMeshFile(tgt_path)
    
    tgt_deformed_path = Path(r"d:\Projects\Head_Neck_Marker_Alignment\data\miccai_2025_data\1013_tgt_transformed.vtk")
    tgt_deformed_pts = loadMeshFile(tgt_deformed_path)

    fids_path = Path(r"d:\Projects\Head_Neck_Marker_Alignment\data\miccai_2025_data\0013_fids.vtk")
    fids_pts = loadMeshFile(fids_path)

    fids_deformed_path = Path(r"d:\Projects\Head_Neck_Marker_Alignment\data\miccai_2025_data\0013_fids_Deformed.vtk")
    fids_deformed_pts = loadMeshFile(fids_deformed_path)

    #------------------------------- Point Cloud Data -------------------------------#
    pc_path = Path(r"d:\Projects\Head_Neck_Marker_Alignment\data\miccai_2025_data\1013_sparsedata_transformed.vtk")
    bed_pc = loadMeshFile(pc_path)

    bed_fids_path = Path(r"d:\Projects\Head_Neck_Marker_Alignment\data\miccai_2025_data\1013_fids_transformed.vtk")
    bed_fids = loadMeshFile(bed_fids_path)

    bed_tgt_path = Path(r"d:\Projects\Head_Neck_Marker_Alignment\data\miccai_2025_data\1013_tgt_transformed.vtk")
    bed_tgt = loadMeshFile(bed_tgt_path)


    cb = TimerCB(
        bel_mesh,
        bel_deformed_mesh,
        tgt_pts,
        tgt_deformed_pts,
        fids_pts,
        fids_deformed_pts,
        )
    
    # Specimen Mesh Mapper/Actor
    mesh_mapper = vtk.vtkPolyDataMapper()
    mesh_mapper.SetInputData(cb.anim_mesh)
    mesh_actor = vtk.vtkActor()
    mesh_actor.SetMapper(mesh_mapper)

    p = mesh_actor.GetProperty()
    p.SetColor(0.9, 0.7, 0.2)       # RGB in [0,1]
    p.SetOpacity(0.9)              # 0..1
    p.SetRepresentationToSurface()  # Surface | Wireframe | Points
    p.SetEdgeVisibility(True)
    p.SetEdgeColor(0.1, 0.1, 0.1)
    p.SetLineWidth(2.0)             # wireframe/edges width
    p.SetInterpolationToPhong()     # Flat | Gouraud | Phong
    # Optional: point rendering style for point rep
    p.SetPointSize(4)               # pixel size
    mesh_mapper.SetResolveCoincidentTopologyToPolygonOffset()

    
    # Fids Mapper/Actor
    fids_mapper = vtk.vtkPolyDataMapper()
    fids_mapper.SetInputData(cb.anim_fids)
    fids_actor = vtk.vtkActor()
    fids_actor.SetMapper(fids_mapper)

    fids_p = fids_actor.GetProperty()
    fids_p.SetRepresentationToPoints()
    fids_p.SetPointSize(10)           # px size
    fids_p.SetColor(0.0, 0.0, 1.0)
    # fids_mapper.SetRenderPointsAsSpheres(True)         # nice round points (OpenGL)

    # Tgts Mapper/Actor
    tgts_mapper = vtk.vtkPolyDataMapper()
    tgts_mapper.SetInputData(cb.anim_tgt)
    tgts_actor = vtk.vtkActor()
    tgts_actor.SetMapper(tgts_mapper)

    tgts_p = tgts_actor.GetProperty()
    tgts_p.SetRepresentationToPoints()
    tgts_p.SetPointSize(10)           # px size
    tgts_p.SetColor(1.0, 0.0, 0.0)


    # bed pc Mapper/Actor
    bed_pc_mapper = vtk.vtkPolyDataMapper()
    bed_pc_mapper.SetInputData(bed_pc)
    bed_pc_actor = vtk.vtkActor()
    bed_pc_actor.SetMapper(bed_pc_mapper)

    bed_pc_p = bed_pc_actor.GetProperty()
    bed_pc_p.SetRepresentationToPoints()
    bed_pc_p.SetPointSize(1)           # px size
    bed_pc_p.SetColor(0.8, 0.8, 0.8)

    # bed tgt Mapper/Actor
    bed_tgts_mapper = vtk.vtkPolyDataMapper()
    bed_tgts_mapper.SetInputData(bed_tgt)
    bed_tgts_actor = vtk.vtkActor()
    bed_tgts_actor.SetMapper(bed_tgts_mapper)

    bed_tgts_p = bed_tgts_actor.GetProperty()
    bed_tgts_p.SetRepresentationToPoints()
    bed_tgts_p.SetPointSize(10)           # px size
    bed_tgts_p.SetColor(1.0, 0.0, 1.0)

    # bed fids Mapper/Actor
    bed_fids_mapper = vtk.vtkPolyDataMapper()
    bed_fids_mapper.SetInputData(bed_fids)
    bed_fids_actor = vtk.vtkActor()
    bed_fids_actor.SetMapper(bed_fids_mapper)

    bed_fids_p = bed_fids_actor.GetProperty()
    bed_fids_p.SetRepresentationToPoints()
    bed_fids_p.SetPointSize(10)           # px size
    bed_fids_p.SetColor(0.0, 1.0, 1.0)

    ren = vtk.vtkRenderer()
    ren.AddActor(mesh_actor)
    ren.AddActor(fids_actor)
    ren.AddActor(tgts_actor)
    ren.AddActor(bed_pc_actor)
    ren.AddActor(bed_tgts_actor)
    ren.AddActor(bed_fids_actor)
    win = vtk.vtkRenderWindow()
    win.AddRenderer(ren)
    win.SetSize(1080, 1080)
    iren = vtk.vtkRenderWindowInteractor()
    iren.SetRenderWindow(win)

    iren.Initialize()
    win.Render()  # show the first frame

    print(tgt_deformed_pts)
    print(tgt_pts)
    iren.Initialize()
    win.Render()

    cb.timer_id = iren.CreateRepeatingTimer(60)  # ~60 FPS
    iren.AddObserver("TimerEvent", cb.execute)

    iren.Start()


        
        
        # win.Render()
        # iren.ProcessEvents()
        # time.sleep(0.5)

