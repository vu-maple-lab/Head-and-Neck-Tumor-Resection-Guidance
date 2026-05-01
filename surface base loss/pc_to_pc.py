import vtk
import numpy as np

def read_vtk(filename):
    reader = vtk.vtkPolyDataReader()
    reader.SetFileName(filename)
    reader.Update()

    polydata = reader.GetOutput()
    points = polydata.GetPoints()
    num_points = points.GetNumberOfPoints()
    vtk_points = np.zeros((num_points, 3))

    for i in range(num_points):
        vtk_points[i] = points.GetPoint(i)

    return vtk_points

def distance(points1, points2):
    dist1 = np.sqrt(np.sum((points1[:, np.newaxis] - points2) ** 2, axis=-1)).min(axis=-1)
    dist2 = np.sqrt(np.sum((points2[:, np.newaxis] - points1) ** 2, axis=-1)).min(axis=-1)
    print(dist1)
    print(dist2)
    chamfer_dist = np.mean(dist1) + np.mean(dist2)
    hausdorff_dist = np.max([np.max(dist1),np.max(dist2)])

    result = [chamfer_dist, hausdorff_dist]
    return result

# Rigid Alignment All
num = input("Enter the Specimen Number:")

vtk_file1 = "C:/Users/qingyun/Desktop/surface base loss/FEM/Pt_00000{0}/sparsedata_reg.vtk".format(num)
vtk_file2 = "C:/Users/qingyun/Desktop/surface base loss/Pt_00000{0}/testBefore_reg.vtk".format(num)
vtk_file3 = "C:/Users/qingyun/Desktop/surface base loss/FEM/Pt_00000{0}/testAfter_reg.vtk".format(num)

# vtk_file1 = "C:/Users/qingyun/Desktop/1003_sparsedata.vtk"
# vtk_file2 = "C:/Users/qingyun/Desktop/testAfter.vtk"
# vtk_file3 = "C:/Users/qingyun/Desktop/testBefore.vtk"


points1 = read_vtk(vtk_file1)
points2 = read_vtk(vtk_file2)
points3 = read_vtk(vtk_file3)

chamfer_dist = distance(points1, points3)[0]
hausdorff_dist = distance(points1, points3)[1]

chamfer_dist_deform = distance(points1, points2)[0]
hausdorff_dist_deform = distance(points1, points2)[1]

print(f"Chamfer Distance between the 3d scanning and the cavity: {chamfer_dist}")
print(f"Chamfer Distance between the deformed model and the cavity: {chamfer_dist_deform}")

print(f"Hausdorff Distance between the 3d scanning and the cavity: {hausdorff_dist}")
print(f"Hausdorff Distance between the deformed model and the cavity: {hausdorff_dist_deform}")
