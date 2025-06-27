import numpy as np
import vtk
import open3d as o3d
import os
import pyzed.sl as sl


def save_data(
    cam,
    dense_point_cloud,
    image_size_dense,
    data_list,
    filepath,
    frame_id,
    file_name,
    reference_PC=[]
):
    """
    Save the selected 3D points (from ROI or SAM segmentation) to a VTK file.

    Optionally also visualize with Open3D, e.g., for fiducial or border points.

    Args:
        cam (sl.Camera): ZED camera object
        dense_point_cloud (sl.Mat): ZED dense point cloud
        image_size_dense (sl.Resolution): ZED resolution for point cloud
        data_list (list of (x,y)): pixel coordinates selected by user
        filepath (str): path to the .svo file
        frame_id (int): current frame index
        file_name (str): label name, e.g. "fids", "SAM"
        reference_PC (list of (x,y), optional): coordinates for a second point cloud

    Returns:
        bool: True if save was successful, False if user decided to re-select
    """

    # get XYZRGBA data from the ZED camera
    cam.retrieve_measure(dense_point_cloud, sl.MEASURE.XYZRGBA, sl.MEM.CPU, image_size_dense)
    cam_info = cam.get_camera_information().camera_configuration.resolution
    h, w = cam_info.height, cam_info.width

    # extract xyz coordinates
    xyz = dense_point_cloud.get_data()[:, :, 0:3]
    # extract rgba, then get rgb
    rgba = np.ravel(dense_point_cloud.get_data()[:, :, 3]).view("uint8").reshape((h, w, 4))
    rgb = rgba[:, :, 0:3]

    # concatenate into (h, w, 6)
    xyzrgb = np.concatenate((xyz, rgb), axis=-1)

    roi_points = []
    for x, y in data_list:
        if 0 <= x < w and 0 <= y < h:
            point = xyzrgb[y, x]
            if np.isfinite(point).all():
                roi_points.append(point)

    reference_points = []
    if reference_PC:
        for x, y in reference_PC:
            if 0 <= x < w and 0 <= y < h:
                point = xyzrgb[y, x]
                if np.isfinite(point).all():
                    reference_points.append(point)

    roi_points = np.array(roi_points)
    reference_points = np.array(reference_points)

    # convert to vtk structures
    vtk_points = vtk.vtkPoints()
    vertices = vtk.vtkCellArray()
    vtk_colors = vtk.vtkUnsignedCharArray()
    vtk_colors.SetNumberOfComponents(3)
    vtk_colors.SetName("Colors")

    # insert points into vtk structure
    for point in roi_points:
        x, y, z = point[:3]
        r, g, b = point[3:6]
        pid = vtk_points.InsertNextPoint(x, y, z)
        vtk_colors.InsertNextTuple3(int(r), int(g), int(b))
        vertices.InsertNextCell(1)
        vertices.InsertCellPoint(pid)

    # optionally visualize with open3d
    if file_name in {"fids", "SAM", "tgt", "arUco"}:
        pcd_fids = o3d.geometry.PointCloud()
        roi_xyz = roi_points[:, 0:3]
        pcd_fids.points = o3d.utility.Vector3dVector(roi_xyz)
        pcd_fids.colors = o3d.utility.Vector3dVector(np.tile([1, 0, 0], (len(roi_xyz), 1)))  # red

        if file_name != "SAM":
            pcd_target = o3d.geometry.PointCloud()
            target_xyz = reference_points[:, 0:3]
            pcd_target.points = o3d.utility.Vector3dVector(target_xyz)
            pcd_target.colors = o3d.utility.Vector3dVector(np.tile([0, 0, 1], (len(target_xyz), 1)))  # blue
            o3d.visualization.draw_geometries([pcd_fids, pcd_target])
        else:
            o3d.visualization.draw_geometries([pcd_fids])

        print(f"Visualized {len(roi_xyz)} points.")
        if_select = input("Re-Select? (T/F) ")
        if if_select.upper() == "T":
            return False

    # pack VTK polydata
    polydata = vtk.vtkPolyData()
    polydata.SetPoints(vtk_points)
    if file_name in {"fids", "tgt", "arUco"}:
        polydata.SetVerts(vertices)
    polydata.GetPointData().SetScalars(vtk_colors)

    # organize file name
    base_dir = os.path.dirname(filepath)
    base_filename = os.path.splitext(os.path.basename(filepath))[0]
    dir_path = os.path.join(base_dir, base_filename)
    os.makedirs(dir_path, exist_ok=True)

    vtk_path = os.path.join(dir_path, f"frame{frame_id:04d}_{file_name}.vtk")

    writer = vtk.vtkPolyDataWriter()
    writer.SetFileName(vtk_path)
    writer.SetInputData(polydata)
    writer.Write()
    print(f"Saved frame {frame_id:04d} to {vtk_path}")
    return True


def selectPointsBorder(
    img_crop,
    cam,
    selectRegionROI,
    dense_point_cloud,
    image_size_dense,
    filepath,
    prompt,
    frame_id,
    reference_PC=[]
):
    """
    Helper function to open a GUI for selecting boundary or marker points.

    Args:
        img_crop (np.ndarray): cropped region of the image
        cam (sl.Camera): ZED camera object
        selectRegionROI (tuple): (x,y,w,h) crop offset for mapping back
        dense_point_cloud (sl.Mat): ZED dense point cloud
        image_size_dense (sl.Resolution): ZED resolution
        filepath (str): path to the .svo
        prompt (str): label for saved file, e.g. "arUco"
        frame_id (int): current frame index
        reference_PC (list of (x,y), optional): second reference points for visualization

    Returns:
        bool: True if saved, False if user wants to reselect
    """
    from gui_utils import CorrectDotsGUI

    gui = CorrectDotsGUI(img_crop)
    gui.run()

    if not gui.centroids:
        print("No points or border selected, quitting.")
        cam.close()
        return

    # offset back to the original coordinates
    marker_centroids = []
    if prompt == "arUco":
        marker_centroids = gui.centroids
    else:
        for pt in gui.centroids:
            marker_centroids.append((pt[0] + selectRegionROI[0], pt[1] + selectRegionROI[1]))

    reselect = save_data(
        cam,
        dense_point_cloud,
        image_size_dense,
        marker_centroids,
        filepath,
        frame_id,
        prompt,
        reference_PC,
    )
    if not reselect:
        return False
    return True
