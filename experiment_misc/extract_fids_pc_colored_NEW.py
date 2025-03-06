import pyzed.sl as sl
import math
import numpy as np
import sys
import cv2
import os
import vtk
import logging
from matplotlib import pyplot as plt
import open3d as o3d

class BoundingBoxGUI:
    def __init__(self, image):
        self.image = image.copy()
        self.orig_image = image.copy()
        self.bboxes = []
        self.current_box = None
        self.mouse_down = False
        cv2.namedWindow('image', cv2.WINDOW_KEEPRATIO)
        # cv2.resizeWindow('image', 200, 200)
        cv2.setMouseCallback('image', self.mouse_callback)

    def mouse_callback(self, event, x, y, flags, params):
        if event == cv2.EVENT_LBUTTONDOWN:
            self.mouse_down = True
            self.current_box = (x, y, 0, 0)
        elif event == cv2.EVENT_MOUSEMOVE:
            if self.mouse_down:
                w = x - self.current_box[0]
                h = y - self.current_box[1]
                self.current_box = (self.current_box[0], self.current_box[1], w, h)
        elif event == cv2.EVENT_LBUTTONUP:
            self.mouse_down = False
            self.bboxes.append(self.current_box)
            self.current_box = None
        elif event == cv2.EVENT_RBUTTONDOWN:
            for bbox in self.bboxes:
                if bbox[0] <= x <= bbox[0] + bbox[2] and bbox[1] <= y <= bbox[1] + bbox[3]:
                    self.bboxes.remove(bbox)
                    self.draw_boxes()

    def draw_boxes(self):
        for box in self.bboxes:
            cv2.rectangle(self.image, (box[0], box[1]), (box[0] + box[2], box[1] + box[3]), (0, 255, 0), 2)

    def run(self):
        while True:
            self.image = self.orig_image.copy()
            self.draw_boxes()
            cv2.imshow('image', self.image)
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('d'):
                if len(self.bboxes) > 0:
                    self.bboxes.pop()
        cv2.destroyAllWindows()


class CorrectDotsGUI:
    def __init__(self, image):
        self.image = image.copy()
        self.orig_image = image.copy()
        self.centroids = []
        self.current_centroid = None
        self.border = []
        self.current_border = None
        self.mouse_down = False
        self.draw_bolder = False

        cv2.namedWindow('image', cv2.WINDOW_KEEPRATIO)
        # cv2.resizeWindow('image', 200, 200)
        cv2.setMouseCallback('image', self.mouse_callback)

    def mouse_callback(self, event, x, y, flags, params):
        # Press "ctrl" to collect data
        if event == cv2.EVENT_MOUSEMOVE and flags & cv2.EVENT_FLAG_CTRLKEY:
            self.current_border = (x, y)
            self.border.append(self.current_border)
            self.current_border = None

        elif event == cv2.EVENT_LBUTTONDOWN:
            self.mouse_down = True
            self.current_centroid = (x, y)

        elif event == cv2.EVENT_LBUTTONUP:
            self.mouse_down = False
            self.centroids.append(self.current_centroid)
            self.current_centroid = None

        elif event == cv2.EVENT_RBUTTONDOWN:
            for centroid in self.centroids:
                if centroid[0] - 15 <= x <= centroid[0] + 15 and centroid[1] - 15 <= y <= centroid[1] + 15:
                    self.centroids.remove(centroid)
                    self.draw_centroids("fids")

        # Press "alt" to delete collected data
        elif event == cv2.EVENT_MOUSEMOVE and flags & cv2.EVENT_FLAG_ALTKEY:
            for border in self.border:
                if border[0] - 7 <= x <= border[0] + 7 and border[1] - 7 <= y <= border[1] + 7:
                    self.border.remove(border)
                    self.draw_centroids("border")

    def draw_centroids(self, prompt):
        if(prompt == "fids" or prompt == "tgt"):
            for centroid in self.centroids:
                cv2.circle(self.image, (centroid[0], centroid[1]), 3, (0, 255, 0), 2)
        else:
            for border in self.border:
                cv2.circle(self.image, (border[0], border[1]), 3, (0, 255, 0), 2)

    def run(self, prompt):
        while True:
            self.image = self.orig_image.copy()
            self.draw_centroids(prompt)
            cv2.imshow('image', self.image)

            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('d'):
                if (prompt == "fids" or prompt == "tgt"):
                    if len(self.centroids) > 0:
                        self.centroids.pop()
                else:
                    if len(self.border) > 0:
                        self.border.pop()

        cv2.destroyAllWindows()

def save_data(cam, dense_point_cloud, image_size_dense, data_list, filepath, frame_id, fileName):
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

    roi_points = np.array(roi_points)  

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
    if fileName == "fids":
        # # 归一化颜色值
        # rgb_normalized = rgb / 255.0

        # # 创建原始点云
        # pcd = o3d.geometry.PointCloud()
        # pcd.points = o3d.utility.Vector3dVector(xyz.reshape(-1, 3))  # 设置点云坐标
        # pcd.colors = o3d.utility.Vector3dVector(rgb_normalized.reshape(-1, 3))  # 设置点云颜色

        pcd_fids = o3d.geometry.PointCloud()
        roi_xyz = roi_points[:, 0:3]  # 提取 XYZ 坐标
        pcd_fids.points = o3d.utility.Vector3dVector(roi_xyz)

        red_color = np.tile([1, 0, 0], (len(roi_xyz), 1)) 
        pcd_fids.colors = o3d.utility.Vector3dVector(red_color)

        # 可视化点云
        o3d.visualization.draw_geometries([pcd_fids])

        ifSelectFids = input("Re-Select fids?(T/F)")
        if(ifSelectFids == "T"):
            return False

    # Create polydata object
    polydata = vtk.vtkPolyData()
    polydata.SetPoints(vtk_points)
    if (fileName == "fids" or fileName == "tgt"):
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

# Select fiducial points and border
def selectPointsBorder(img_crop, cam, selectRegionROI, dense_point_cloud, image_size_dense, filepath, prompt):
    selectPointsGUI = CorrectDotsGUI(img_crop)
    selectPointsGUI.run(prompt)

    if (((prompt == "fids" or prompt == "tgt") and (not selectPointsGUI.centroids)) or (prompt == "border" and (not selectPointsGUI.border))):
        print("No points or border are selected")
        cam.close()
        return
    
    crop_centroids = selectPointsGUI.centroids if (prompt == "fids" or prompt == "tgt") else selectPointsGUI.border

    marker_centroids = []
    for point in crop_centroids:
        thisPoint = (point[0] + selectRegionROI[0], point[1] + selectRegionROI[1])
        marker_centroids.append(thisPoint)

    reSelect = save_data(cam, dense_point_cloud, image_size_dense, marker_centroids, filepath, frame_id, prompt)
    if not reSelect:
        return False
    return True

def process_svo(filepath, frame_id):
    print(f"Reading SVO file: {filepath}")

    input_type = sl.InputType()
    input_type.set_from_svo_file(filepath)
    init = sl.InitParameters(input_t=input_type, depth_mode=sl.DEPTH_MODE.NEURAL, coordinate_units=sl.UNIT.METER)
    cam = sl.Camera()
    status = cam.open(init)
    if status != sl.ERROR_CODE.SUCCESS:
        print(repr(status))
        exit()

    ds_factor = 1
    dense_point_cloud = sl.Mat(cam.get_camera_information().camera_configuration.resolution.width,
                               cam.get_camera_information().camera_configuration.resolution.height,
                               sl.MAT_TYPE.F32_C4)
    print(cam.get_camera_information().camera_configuration.resolution.width)
    sparse_point_cloud = sl.Mat(cam.get_camera_information().camera_configuration.resolution.width // ds_factor,
                                cam.get_camera_information().camera_configuration.resolution.height // ds_factor,
                                sl.MAT_TYPE.F32_C4)
    image_size_dense = cam.get_camera_information().camera_configuration.resolution
    image_size_sparse = cam.get_camera_information().camera_configuration.resolution
    image_size_sparse.width = sparse_point_cloud.get_width()
    image_size_sparse.height = sparse_point_cloud.get_height()

    runtime = sl.RuntimeParameters()
    mat = sl.Mat()

    # Set the SVO position to the specified frame
    cam.set_svo_position(frame_id)

    # Read the specified frame
    if cam.grab(runtime) == sl.ERROR_CODE.SUCCESS:
        cam.retrieve_image(mat, sl.VIEW.LEFT)

        # Select region of interest
        selectRegionGUI = BoundingBoxGUI(mat.get_data())
        selectRegionGUI.run()
        if not selectRegionGUI.bboxes:
            print("No bounding box selected")
            cam.close()
            return
        selectRegionROI = selectRegionGUI.bboxes[0]

        # Set ROI
        print("Set region of interest")
        img_mask = sl.Mat(image_size_dense.width, image_size_dense.height, sl.MAT_TYPE.U8_C1)
        img_mask.set_to(0)
        for i in range(selectRegionROI[0], selectRegionROI[0] + selectRegionROI[2]):
            for j in range(selectRegionROI[1], selectRegionROI[1] + selectRegionROI[3]):
                img_mask.set_value(i, j, 1)
        cam.set_region_of_interest(img_mask)

        img_crop = mat.get_data()[selectRegionROI[1]:(selectRegionROI[1] + selectRegionROI[3]),
                   selectRegionROI[0]:(selectRegionROI[0] + selectRegionROI[2]), :]
        
        print(selectRegionROI)
        # print(img_crop)
        # Select fids and boarder
        ifSelectFids = input("Select fids?(T/F)")
        if(ifSelectFids == "T"):
            reSelect = False
            while(not reSelect) :
                reSelect = selectPointsBorder(img_crop, cam, selectRegionROI, dense_point_cloud, image_size_dense, filepath, "fids")

        ifSelectFids = input("Select target?(T/F)")
        if(ifSelectFids == "T"):
            reSelect = False
            while(not reSelect) :
                reSelect = selectPointsBorder(img_crop, cam, selectRegionROI, dense_point_cloud, image_size_dense, filepath, "tgt")

        ifSelectBorder = input("Select border?(T/F)")
        if(ifSelectBorder == "T"):
            selectPointsBorder(img_crop, cam, selectRegionROI, dense_point_cloud, image_size_dense, filepath, "border")
            
        # Save ROI pointclouds
        roi_list = []
        for i in range(selectRegionROI[0], selectRegionROI[0] + selectRegionROI[2]):
            for j in range(selectRegionROI[1], selectRegionROI[1] + selectRegionROI[3]):
                thisPoint = (i, j)
                roi_list.append(thisPoint)

        save_data(cam, dense_point_cloud, image_size_dense, roi_list, filepath, frame_id, "PC")

    cam.close()


def select_frame(filepath):
    # 通过创建一个 sl.InputType() 对象，你可以设置输入源的类型，例如从 SVO 文件（Stereo Video File）读取数据。
    input_type = sl.InputType()

    # 在你的代码中，input_type = sl.InputType() 创建了一个 sl.InputType 的实例，然后通过 set_from_svo_file(filepath) 方法，
    # 将 SVO 文件的路径传递给这个对象，以指定数据来源。
    input_type.set_from_svo_file(filepath)

    # 创建了一个用于初始化相机的参数对象。
    # input_t=input_type 将之前创建的 input_type 对象（用于指定输入源类型）传递给了初始化参数对象。
    # 这告诉 ZED SDK 要使用之前设置的输入类型（即从 SVO 文件中读取数据）。
    init = sl.InitParameters(input_t=input_type, depth_mode=sl.DEPTH_MODE.NEURAL, coordinate_units=sl.UNIT.METER)
    cam = sl.Camera()
    status = cam.open(init)
    if status != sl.ERROR_CODE.SUCCESS:
        print(repr(status))
        exit()

    # Obtain the total number of frames in .svo file
    total_frames = cam.get_svo_number_of_frames()
    print(total_frames)

    frame_id = 0

    while True:
        # Seek to the current frame
        cam.set_svo_position(frame_id)

        # Grab the current frame
        if cam.grab() == sl.ERROR_CODE.SUCCESS:
            # Retrieve the left image
            # sl.Mat 对象用于表示单个图像帧的图像数据。
            mat = sl.Mat(cam.get_camera_information().camera_configuration.resolution.width
                               , cam.get_camera_information().camera_configuration.resolution.height
                               , sl.MAT_TYPE.F32_C4)

            # 用于从 ZED 相机中检索左侧视图的图像数据，并将其存储到 sl.Mat 对象 mat 中。
            cam.retrieve_image(mat, sl.VIEW.LEFT)

            # 使用 mat.get_data() 来获取图像数据的 NumPy 数组表示。
            # 这样，cv2_image = mat.get_data() 就得到了左侧视图的图像数据，
            # 可以在后续的处理中使用 OpenCV 或其他库来进一步处理、显示或保存图像。
            cv2_image = mat.get_data()

            cv2.namedWindow("image", cv2.WINDOW_KEEPRATIO)
            cv2.imshow("image", cv2_image)
            key = cv2.waitKey(0)
            if key == ord('l'):
                frame_id = max(frame_id - 1, 0)
            elif key == ord('r'):
                frame_id = min(frame_id + 1, total_frames - 1)
            elif key == ord('q'):
                break
        else:
            print("No image data available.")

    cv2.destroyAllWindows()
    cam.close()
    return frame_id

if __name__ == "__main__":

    # num = input('Enter your Specimen Number:')
    # svo_files = "C:\\Users\\qingyun\\Desktop\\DataProcess\\000{0}.svo".format(num)
    # svo_files = r"C:\Users\qingyun\Desktop\New_intra\0023\0023_cav.svo"
    # svo_files = r"D:\Projects\Head_Neck_Marker_Alignment\data\EXP\20250206_run\run0\HD2K_SN38709915_10-48-18.svo"
    svo_files = r"D:\Projects\Head_Neck_Marker_Alignment\data\EXP\20250206_run\run2\0024_cav.svo"
    svo_files = r"D:\Projects\Head_Neck_Marker_Alignment\data\EXP\20250206_run\run0\0022\0022_cav\0022_cav.svo"
    svo_files = r"D:\Projects\Head_Neck_Marker_Alignment\data\EXP\20250206_run\run0\0022\0022_up.svo"
    # select one frame from .sov file 
    while True:
        ifSelectFrame = input("Select frame manually (T) or enter a frame number (F)? ")
        if ifSelectFrame == "T": 
            frame_id = select_frame(svo_files)
            break
        elif ifSelectFrame == "F":
            frame_id = int(input("Enter Frame Number:"))
            break
        else:
            print("Invalid input. Please enter 'T' or 'F'.")

    print(frame_id)

    # process the frame
    process_svo(svo_files,frame_id)