import numpy as np
import vtk
import open3d as o3d
import os
import pyzed.sl as sl

def save_data(cam, dense_point_cloud, image_size_dense, data_list, filepath, frame_id, fileName, reference_PC=[]):
    # 提取点云数据 (XYZ 和 RGBA)
    cam.retrieve_measure(dense_point_cloud, sl.MEASURE.XYZRGBA, sl.MEM.CPU, image_size_dense)
    h, w = cam.get_camera_information().camera_configuration.resolution.height, cam.get_camera_information().camera_configuration.resolution.width
    xyz = dense_point_cloud.get_data()[:, :, 0:3]  # 提取 X, Y, Z 坐标
    rgba = np.ravel(dense_point_cloud.get_data()[:, :, 3]).view('uint8').reshape((h, w, 4))  # 提取 RGBA 数据
    rgb = rgba[:, :, 0:3]  # 只保留 RGB 数据

    # Combine XYZ and RGB into one array
    xyzrgb = np.concatenate((xyz, rgb), axis=-1)  # Shape: (h, w, 6)
    print(xyzrgb.shape)

    # 只提取 ROI 中的点
    roi_points = []
    for (x, y) in data_list:
        if 0 <= x < w and 0 <= y < h:
            point = xyzrgb[y, x]
            if np.isfinite(point).all():
                roi_points.append(point)

    reference_points = []
    if reference_PC != []:
        for (x, y) in reference_PC:
            if 0 <= x < w and 0 <= y < h:
                point = xyzrgb[y, x]
                if np.isfinite(point).all():
                    reference_points.append(point)

    roi_points = np.array(roi_points)
    reference_points = np.array(reference_points)

    vtk_points = vtk.vtkPoints()
    vertices = vtk.vtkCellArray()
    vtk_colors = vtk.vtkUnsignedCharArray()
    vtk_colors.SetNumberOfComponents(3)  # RGB components
    vtk_colors.SetName("Colors")

    # Iterate through all points in the ROI
    for point in roi_points:
        x, y, z = point[:3]
        r, g, b = point[3:6]

        # Add points and colors
        pid = vtk_points.InsertNextPoint(x, y, z)
        vtk_colors.InsertNextTuple3(int(r), int(g), int(b))
        vertices.InsertNextCell(1)
        vertices.InsertCellPoint(pid)

    # 3D vision
    if fileName == "fids" or fileName == "SAM" or fileName == "tgt" or fileName == "arUco":
        pcd_fids = o3d.geometry.PointCloud()
        roi_xyz = roi_points[:, 0:3]  # 提取 XYZ 坐标
        pcd_fids.points = o3d.utility.Vector3dVector(roi_xyz)

        red_color = np.tile([1, 0, 0], (len(roi_xyz), 1))
        pcd_fids.colors = o3d.utility.Vector3dVector(red_color)

        # Create another point cloud for another set of points
        if not fileName == "SAM":
            pcd_target = o3d.geometry.PointCloud()
            target_xyz = reference_points[:, 0:3] 
            pcd_target.points = o3d.utility.Vector3dVector(target_xyz)

            blue_color = np.tile([0, 0, 1], (len(target_xyz), 1))  # Blue color for target points
            pcd_target.colors = o3d.utility.Vector3dVector(blue_color)
            o3d.visualization.draw_geometries([pcd_fids, pcd_target])
        else:
            o3d.visualization.draw_geometries([pcd_fids])

        print(len(roi_xyz))
        ifSelectFids = input("Re-Select?(T/F)")
        if(ifSelectFids == "T"):
            return False

    # Create polydata object
    polydata = vtk.vtkPolyData()
    polydata.SetPoints(vtk_points)
    if (fileName == "fids" or fileName == "tgt" or fileName == "arUco"):
        polydata.SetVerts(vertices)
    polydata.GetPointData().SetScalars(vtk_colors)

    base_dir = os.path.dirname(filepath)
    base_filename = os.path.basename(filepath).rsplit('.', 1)[0]  # Remove the .svo extension
    dir_path = os.path.join(base_dir, base_filename)

    if not os.path.exists(dir_path):
        os.makedirs(dir_path)

    # Format frame_id properly
    frame_id_str = f'{frame_id:04d}'  # Ensure frame_id is properly formatted
    vtk_filepath = os.path.join(dir_path, f'frame{frame_id_str}_{fileName}.vtk')

    writer = vtk.vtkPolyDataWriter()
    writer.SetFileName(vtk_filepath)
    writer.SetInputData(polydata)
    writer.Write()
    print(f"Saved frame {frame_id_str} to {vtk_filepath}")
    return True

def selectPointsBorder(img_crop, cam, selectRegionROI, dense_point_cloud, image_size_dense, filepath, prompt, frame_id, reference_PC = []):
    from gui_utils import CorrectDotsGUI
    selectPointsGUI = CorrectDotsGUI(img_crop)
    selectPointsGUI.run()

    if (not selectPointsGUI.centroids):
        print("No points or border are selected")
        cam.close()
        return

    crop_centroids = selectPointsGUI.centroids

    marker_centroids = []
    if prompt == "arUco":
        marker_centroids = crop_centroids
    else:
        for point in crop_centroids:
            thisPoint = (point[0] + selectRegionROI[0], point[1] + selectRegionROI[1])
            marker_centroids.append(thisPoint)

    reSelect = save_data(cam, dense_point_cloud, image_size_dense, marker_centroids, filepath, frame_id, prompt, reference_PC)
    if not reSelect:
        return False
    return True