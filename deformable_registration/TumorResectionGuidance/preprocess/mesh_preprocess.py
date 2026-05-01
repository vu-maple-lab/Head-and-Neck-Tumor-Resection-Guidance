import open3d as o3d
import os
import numpy as np
import vtk
from vtk.util import numpy_support

def read_vtk(file_path):
    reader = vtk.vtkDataSetReader()
    reader.SetFileName(file_path)
    reader.Update()
    output = reader.GetOutput()

    if output.IsA("vtkUnstructuredGrid"):
        print(f"Input {file_path} is vtkUnstructuredGrid. Converting to vtkPolyData...")
        geometry_filter = vtk.vtkGeometryFilter()
        geometry_filter.SetInputData(output)
        geometry_filter.Update()
        return geometry_filter.GetOutput()
    elif output.IsA("vtkPolyData"):
        print(f"Input {file_path} is vtkPolyData.")
        return output
    else:
        raise ValueError(f"Unsupported data type in {file_path}: {output.GetClassName()}")
    
def decimate_mesh(mesh, target_vertices):
    decimate = vtk.vtkDecimatePro()
    decimate.SetInputData(mesh)

    decimate.SetTargetReduction(1.0 - target_vertices / mesh.GetNumberOfPoints()) 
    decimate.Update()

    return decimate.GetOutput()

def scale_fids(mesh, scale_factor):
    transform = vtk.vtkTransform()
    transform.Scale(scale_factor, scale_factor, scale_factor)

    transform_filter = vtk.vtkTransformPolyDataFilter()
    transform_filter.SetInputData(mesh)
    transform_filter.SetTransform(transform)
    transform_filter.Update()

    return transform_filter.GetOutput()

def visualize_mesh(vtk_mesh):
    # Convert vtkPolyData to Open3D mesh format
    points = numpy_support.vtk_to_numpy(vtk_mesh.GetPoints().GetData())
    
    # Extract the connectivity information from vtkCellArray
    cells = vtk_mesh.GetPolys()
    cells.InitTraversal()
    
    triangles = []
    id_list = vtk.vtkIdList()
    
    # Traverse through all the cells (faces)
    while cells.GetNextCell(id_list):
        triangles.append([id_list.GetId(i) for i in range(id_list.GetNumberOfIds())])
    
    # Convert the list of triangles into a NumPy array
    triangles = np.array(triangles)
    
    # Create Open3D mesh from points and triangles
    open3d_mesh = o3d.geometry.TriangleMesh()
    open3d_mesh.vertices = o3d.utility.Vector3dVector(points)
    open3d_mesh.triangles = o3d.utility.Vector3iVector(triangles)
    
    # Compute vertex normals for better visualization
    open3d_mesh.compute_vertex_normals()
    
    # Set mesh rendering properties
    open3d_mesh.paint_uniform_color([0.7, 0.7, 0.7])  # Set mesh color (gray)
    
    # Create a wireframe version of the mesh
    wireframe = o3d.geometry.LineSet.create_from_triangle_mesh(open3d_mesh)
    
    # Visualize the mesh and wireframe together
    o3d.visualization.draw_geometries(
        [open3d_mesh, wireframe],
        window_name="Triangle Mesh Visualization",
        mesh_show_wireframe=True,  # Enable wireframe overlay
        mesh_show_back_face=True,  # Show back faces
    )
    
    return open3d_mesh

def write_vtk(polydata, file_path, if_fids):
    if if_fids:
        if not polydata.GetPoints():
            raise ValueError("Input polydata has no points to write.")

        # Check if the cell structure exist
        # If not, create
        if not polydata.GetPolys().GetNumberOfCells() and not polydata.GetVerts().GetNumberOfCells():
            print("Warning: No cells found in polydata. Adding vertex cells for each point.")
            vertices = vtk.vtkCellArray()
            for i in range(polydata.GetNumberOfPoints()):
                vertices.InsertNextCell(1)
                vertices.InsertCellPoint(i)
            polydata.SetVerts(vertices)

    writer = vtk.vtkPolyDataWriter()
    writer.SetFileName(file_path)
    writer.SetInputData(polydata)
    writer.SetFileTypeToASCII() 
    writer.Write()
    print(f"Data saved to {file_path} in ASCII format.")

def merge_point_clouds(polydata1, polydata2, index=None):
    points1 = polydata1.GetPoints()
    points2 = polydata2.GetPoints()

    if not points1:
        return polydata2
    if not points2:
        return polydata1

    new_points = vtk.vtkPoints()
    for i in range(points1.GetNumberOfPoints()):
        new_points.InsertNextPoint(points1.GetPoint(i))

    if index is None or index >= points1.GetNumberOfPoints():
        for i in range(points2.GetNumberOfPoints()):
            new_points.InsertNextPoint(points2.GetPoint(i))
    else:
        for i in range(points2.GetNumberOfPoints()):
            new_points.InsertPoint(index + i, points2.GetPoint(i))

    merged_polydata = vtk.vtkPolyData()
    merged_polydata.SetPoints(new_points)

    return merged_polydata

def main():
    # Change Dir ############################################################
    base_dir = r"C:\Users\qingyun\Desktop\preprocess\data\Pt_000005\0005"
    id = base_dir[-4:]
    input_mesh_path = os.path.join(base_dir, "mesh.vtk")
    input_fids_path = os.path.join(base_dir, "fids.vtk")

    decimate_factor = 30000 
    if_redecimate = True
    while if_redecimate:
        input_mesh = read_vtk(input_mesh_path)
        decimated_mesh = decimate_mesh(input_mesh, decimate_factor)
        visualize_mesh(decimated_mesh)
        if_redo = input("re-decimate? (T/F)")
        if if_redo == "T":
            decimate_factor = input("decimate factor (default = 30000): ")
            try:
                decimate_factor = int(decimate_factor)
            except ValueError:
                print("Invalid input. Using default value 30000.")
                decimate_factor = 30000
        else:
            if_redecimate = False

    input_fids = read_vtk(input_fids_path)
    scaled_fids = scale_fids(input_fids, 0.001)

    parent_dir = os.path.dirname(base_dir)
    result_path = os.path.join(parent_dir, "PreOperative")
    os.makedirs(result_path, exist_ok=True)
    ouput_mesh_path = os.path.join(result_path, id + "_InputSpecimenForSPMESH.vtk")
    ouput_fids_path = os.path.join(result_path, id + "_fids.vtk")
    
    write_vtk(decimated_mesh, ouput_mesh_path, False)
    write_vtk(scaled_fids, ouput_fids_path, True)
    
    if_tgt = input("Target preprocess? (T/F)")
    if if_tgt:
        input_tgt_path = os.path.join(base_dir, "tgt.vtk")
        input_tgt = read_vtk(input_tgt_path)
        output_tgt_path = os.path.join(result_path, id + "_tgt_mm.vtk")
        write_vtk(input_tgt, output_tgt_path, True)

        while True:
            index_input = input("Index of the tgt (start 0): ")
            if index_input.isdigit():
                index = int(index_input)
                break
            else:
                print("Invalid input. Please enter an integer.")
        merged_tgt = merge_point_clouds(input_fids, input_tgt, index)
        scaled_merged_tgt = scale_fids(merged_tgt, 0.001)
        output_merge_path = os.path.join(result_path, id + "_fids_4.vtk")
        write_vtk(scaled_merged_tgt, output_merge_path, True)

if __name__ == "__main__":
    main()