import vtk
import numpy as np
import open3d as o3d
from vtk.util import numpy_support
import random
import os
from typing import Tuple, List, Optional

# 常量定义
DEFAULT_MASK_FACTOR_OLD = 1200
DEFAULT_MASK_FACTOR_NEW = 2200

class PointCloudProcessor:
    @staticmethod
    def read_vtk(file_path: str) -> vtk.vtkPolyData:
        """读取VTK文件并转换为PolyData格式"""
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
        raise ValueError(f"Unsupported data type in {file_path}: {output.GetClassName()}")

    @staticmethod
    def write_vtk(polydata: vtk.vtkPolyData, file_path: str) -> None:
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
        writer.Write()

    @staticmethod
    def extract_points(polydata: vtk.vtkPolyData) -> np.ndarray:
        """从点云中提取点坐标"""
        return numpy_support.vtk_to_numpy(polydata.GetPoints().GetData())

    @staticmethod
    def rigid_registration(source_points: np.ndarray, target_points: np.ndarray) -> np.ndarray:
        """刚性配准"""
        source_mean = np.mean(source_points, axis=0)
        target_mean = np.mean(target_points, axis=0)
        
        # 中心化点云
        H = (source_points - source_mean).T @ (target_points - target_mean)
        U, _, Vt = np.linalg.svd(H)
        R = Vt.T @ U.T
        
        # 构建变换矩阵
        T = np.eye(4)
        T[:3, :3] = R
        T[:3, 3] = target_mean - R @ source_mean
        
        return T

    @staticmethod
    def apply_transformation(polydata: vtk.vtkPolyData, transformation: np.ndarray) -> vtk.vtkPolyData:
        """应用变换矩阵到点云"""
        points = PointCloudProcessor.extract_points(polydata)
        homogeneous_points = np.column_stack([points, np.ones(len(points))])
        transformed_points = (homogeneous_points @ transformation.T)[:, :3]
        
        transformed_polydata = vtk.vtkPolyData()
        transformed_polydata.DeepCopy(polydata)
        transformed_polydata.GetPoints().SetData(
            numpy_support.numpy_to_vtk(transformed_points)
        )
        return transformed_polydata

    @staticmethod
    def merge_point_clouds(*polydata_list: vtk.vtkPolyData) -> vtk.vtkPolyData:
        """合并多个点云"""
        append_filter = vtk.vtkAppendPolyData()
        for data in polydata_list:
            append_filter.AddInputData(data)
        append_filter.Update()
        return append_filter.GetOutput()

    @staticmethod
    def decimate_point_cloud(polydata: vtk.vtkPolyData, target_points: int) -> vtk.vtkPolyData:
        """降采样点云"""
        points = polydata.GetPoints()
        current_points = points.GetNumberOfPoints()
        
        if target_points >= current_points:
            return polydata

        indices = random.sample(range(current_points), target_points)
        sampled_points = vtk.vtkPoints()
        vertices = vtk.vtkCellArray()

        for i in indices:
            pid = sampled_points.InsertNextPoint(points.GetPoint(i))
            vertices.InsertNextCell(1)
            vertices.InsertCellPoint(pid)

        sampled_polydata = vtk.vtkPolyData()
        sampled_polydata.SetPoints(sampled_points)
        sampled_polydata.SetVerts(vertices)
        return sampled_polydata

    @staticmethod
    def visualize_point_cloud(polydata: vtk.vtkPolyData, window_name: str = "Point Cloud Visualization") -> None:
        """可视化点云"""
        points = PointCloudProcessor.extract_points(polydata)
        pcd = o3d.geometry.PointCloud()
        pcd.points = o3d.utility.Vector3dVector(points)
        o3d.visualization.draw_geometries([pcd], window_name=window_name)

    @classmethod
    def interactive_decimation(cls, polydata: vtk.vtkPolyData, default_points: int, 
                             data_name: str = "") -> vtk.vtkPolyData:
        """交互式降采样"""
        while True:
            decimated = cls.decimate_point_cloud(polydata, default_points)
            cls.visualize_point_cloud(decimated, f"Decimated {data_name} ({default_points} points)")
            
            if input("Re-mask? (T/F): ").upper() != "T":
                return decimated
                
            try:
                default_points = int(input(f"Mask factor (default = {default_points}): ") or default_points)
            except ValueError:
                print(f"Invalid input. Using default value {default_points}.")

def main():
    #Change Dir###################################################
    base_dir = r"C:\Users\qingyun\Desktop\preprocess\data\Pt_0000022\1022"
    patient_id = "1" + base_dir[-3:]
    print(f"Processing patient: {patient_id}")
    
    #Change Dir###################################################
    cav_dir = os.path.join(base_dir, "cav")
    frame_num = "frame0010"
    required_files = {
        "arUco": frame_num + "_arUco.vtk",
        "SAM": frame_num + "_SAM.vtk",
        "fids": frame_num + "_fids.vtk"
    }
    
    # file exist?
    file_paths = {name: os.path.join(cav_dir, fname) for name, fname in required_files.items()}
    for name, path in file_paths.items():
        if not os.path.exists(path):
            raise FileNotFoundError(f"File {path} does not exist.")
    
    processor = PointCloudProcessor()
    arUcoA = processor.read_vtk(file_paths["arUco"])
    SAMA = processor.read_vtk(file_paths["SAM"])
    fidsA = processor.read_vtk(file_paths["fids"])
    
    # Decimate old intra
    decimated_cav = processor.interactive_decimation(
        SAMA, DEFAULT_MASK_FACTOR_OLD, "cavity point cloud"
    )


    parent_dir = os.path.dirname(base_dir)
    deform_input = os.path.join(parent_dir, "IntraOperative")
    os.makedirs(deform_input, exist_ok=True)
    processor.write_vtk(decimated_cav, os.path.join(deform_input, f"{patient_id}_sparsedata.vtk"))
    processor.write_vtk(fidsA, os.path.join(deform_input, f"{patient_id}_fids.vtk"))
    
    # Merge point for AR
    merged_fids = processor.merge_point_clouds(arUcoA, fidsA)

    #Change Dir###################################################
    processor.write_vtk(merged_fids, os.path.join(deform_input, "frame0010_fids.vtk"))
    
    # If process New intra?
    if input("New IntraOperative Model? (T/F): ").upper() == "T":
        up_dir = os.path.join(base_dir, "up")
        #Change Dir###################################################
        frame_num = "frame0010"
        up_files = {
            "SAM": frame_num + "_SAM.vtk",
            "fids": frame_num + "_fids.vtk",
            "arUco": frame_num + "_arUco.vtk", 
            "PC": frame_num + "_PC.vtk"
        }
        
        SAMB = processor.read_vtk(os.path.join(up_dir, up_files["SAM"]))
        PCB = processor.read_vtk(os.path.join(up_dir, up_files["PC"]))

        # Without rigistration
        combined = processor.merge_point_clouds(SAMB, SAMA)
        decimated_combined = processor.interactive_decimation(combined, DEFAULT_MASK_FACTOR_NEW)
            
        processor.write_vtk(
            decimated_combined,
            os.path.join(deform_input, f"{patient_id}_sparsedata_new.vtk")
        )

        # Choose way of rigid reg
        registration_types = []
        if input("Fids registration (T/F): ").upper() == "T":
            registration_types.append(("fids", up_files["fids"]))
        if input("arUco registration (T/F): ").upper() == "T":
            registration_types.append(("arUco", up_files["arUco"]))
        

        for reg_type, fname in registration_types:
            source_data = processor.read_vtk(os.path.join(up_dir, fname))
            
            target_points = processor.extract_points(arUcoA if reg_type == "arUco" else fidsA)
            source_points = processor.extract_points(source_data)
            
            transformation = processor.rigid_registration(source_points, target_points)
            print(f"{reg_type} Transformation Matrix:\n", transformation)
            
            transformed_SAMB = processor.apply_transformation(SAMB, transformation)
            transformed_pt = processor.apply_transformation(arUcoA if reg_type == "arUco" else fidsA, transformation)
            transformed_PC = processor.apply_transformation(PCB, transformation)
            
            processor.write_vtk(
                transformed_SAMB, 
                os.path.join(base_dir, f"SAM_cav_transformed_{reg_type}.vtk")
            )
            processor.write_vtk(
                transformed_pt, 
                os.path.join(base_dir, f"Pt_cav_transformed_{reg_type}.vtk")
            )
            processor.write_vtk(
                transformed_PC, 
                os.path.join(base_dir, f"PC_cav_transformed_{reg_type}.vtk")
            )

            combined = processor.merge_point_clouds(transformed_SAMB, SAMA)
            decimated_combined = processor.interactive_decimation(
                combined, DEFAULT_MASK_FACTOR_NEW, f"combined {reg_type} point cloud"
            )
            
            processor.write_vtk(
                decimated_combined,
                os.path.join(deform_input, f"{patient_id}_sparsedata_new_{reg_type}.vtk")
            )

if __name__ == "__main__":
    main()