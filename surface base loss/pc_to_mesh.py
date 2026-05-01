import vtk
import numpy as np
import point_cloud_utils as pcu

def read_vtk(filename):
    reader = vtk.vtkPolyDataReader()
    reader.SetFileName(filename)
    reader.Update()

    polydata = reader.GetOutput()

    if polydata is None or polydata.GetPoints() is None:
        raise FileNotFoundError(f"Error: Unable to read VTK file or no points found: {filename}")

    points = polydata.GetPoints()
    num_points = points.GetNumberOfPoints()
    vtk_points = np.zeros((num_points, 3))

    for i in range(num_points):
        vtk_points[i] = points.GetPoint(i)

    return vtk_points

def closest_point(pc,mesh):
    v, f = pcu.load_mesh_vf(mesh)

    # Ensure v is of type double (float64)
    v = v.astype(np.float64)

    # Ensure points is of type double (float64)
    pc = pc.astype(np.float64)

    dists, fid, bc = pcu.closest_points_on_mesh(pc, v, f)
    closest_pts = pcu.interpolate_barycentric_coords(f, fid, bc, v)

    return closest_pts
    
def process(vtk,ply):
    points = read_vtk(vtk)
    closest_pts = closest_point(points, ply)

    return [points, closest_pts]

def distance(pc, cavity_mesh, cavity_pc, mesh):
    dist1 = np.sqrt(np.sum((pc[:, np.newaxis] - cavity_mesh) ** 2, axis=-1)).min(axis=-1)
    dist2 = np.sqrt(np.sum((cavity_pc[:, np.newaxis] - mesh) ** 2, axis=-1)).min(axis=-1)
    chamfer_dist = np.mean(dist1) + np.mean(dist2)
    hausdorff_dist = np.max([np.max(dist1), np.max(dist2)])

    result = [chamfer_dist * 1000, hausdorff_dist * 1000]
    return result

# Data Input
num = input("Enter the Specimen Number:")

vtk_file1 = "C:/Users/qingyun/Desktop/surface base loss/FEM/Pt_00000{0}/sparsedata_reg.vtk".format(num)
vtk_file2 = "C:/Users/qingyun/Desktop/surface base loss/Pt_00000{0}/testBefore_reg.vtk".format(num)
vtk_file3 = "C:/Users/qingyun/Desktop/surface base loss/FEM/Pt_00000{0}/testAfter_reg.vtk".format(num)

ply_mesh1 = "C:/Users/qingyun/Desktop/surface base loss/FEM/Pt_00000{0}/sparsedata_mesh.ply".format(num)
ply_mesh2 = "C:/Users/qingyun/Desktop/surface base loss/Pt_00000{0}/testBefore_mesh.ply".format(num)
ply_mesh3 = "C:/Users/qingyun/Desktop/surface base loss/FEM/Pt_00000{0}/testAfter_mesh.ply".format(num)

# PC to cavity mesh
result = process(vtk_file2, ply_mesh1)
pc = result[0]
cavity_mesh = result[1]

result = process(vtk_file1, ply_mesh2)
cavity_pc = result[0]
mesh = result[1]
chamfer_dist, hausdorff_dist = distance(pc, cavity_mesh, cavity_pc, mesh)

result_deform = process(vtk_file3, ply_mesh1)
pc = result_deform[0]
cavity_mesh = result_deform[1]

result_deform = process(vtk_file1, ply_mesh3)
cavity_pc = result_deform[0]
mesh = result_deform[1]
chamfer_dist_deform, hausdorff_dist_deform = distance(pc, cavity_mesh, cavity_pc, mesh)

print(f"Chamfer Distance between the 3d scanning and the cavity: {round(chamfer_dist, 2)} mm")
print(f"Chamfer Distance between the deformed model and the cavity: {round(chamfer_dist_deform, 2)} mm")

print(f"Hausdorff Distance between the 3d scanning and the cavity: {round(hausdorff_dist, 2)} mm")
print(f"Hausdorff Distance between the deformed model and the cavity: {round(hausdorff_dist_deform, 2)} mm")