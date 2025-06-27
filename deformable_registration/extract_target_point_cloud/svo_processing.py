import os
import pyzed.sl as sl
import cv2
from segment_anything import sam_model_registry, SamPredictor
from gui_utils import BoundingBoxGUI, SegmentAnythingGUI
from data_processing import selectPointsBorder, save_data


def process_svo(filepath, frame_id):
    """
    Process a single frame from the given SVO file:
    - Load frame at `frame_id`
    - Let user select ROI via bounding box GUI
    - Optionally use SAM for segmentation on ROI
    - Let user select fiducials, targets, borders, and arUco markers
    - Save point clouds and segmentation results as VTK files

    Args:
        filepath (str): path to the .svo file
        frame_id (int): frame index to process
    """
    print(f"Reading SVO file: {filepath}")

    # Initialize ZED camera input from SVO file
    input_type = sl.InputType()
    input_type.set_from_svo_file(filepath)

    init = sl.InitParameters(input_t=input_type,
                             depth_mode=sl.DEPTH_MODE.NEURAL,
                             coordinate_units=sl.UNIT.METER)
    cam = sl.Camera()
    status = cam.open(init)
    if status != sl.ERROR_CODE.SUCCESS:
        print(f"Failed to open camera: {repr(status)}")
        exit()

    # Prepare dense and sparse point cloud matrices
    resolution = cam.get_camera_information().camera_configuration.resolution
    dense_point_cloud = sl.Mat(resolution.width, resolution.height, sl.MAT_TYPE.F32_C4)
    ds_factor = 1
    sparse_point_cloud = sl.Mat(resolution.width // ds_factor, resolution.height // ds_factor, sl.MAT_TYPE.F32_C4)

    image_size_dense = resolution
    image_size_sparse = resolution
    image_size_sparse.width = sparse_point_cloud.get_width()
    image_size_sparse.height = sparse_point_cloud.get_height()

    runtime = sl.RuntimeParameters()
    mat = sl.Mat()

    # Set SVO frame position and grab frame
    cam.set_svo_position(frame_id)
    if cam.grab(runtime) != sl.ERROR_CODE.SUCCESS:
        print(f"Failed to grab frame {frame_id}")
        cam.close()
        return

    cam.retrieve_image(mat, sl.VIEW.LEFT)

    # Show GUI for user to select ROI bounding box
    selectRegionGUI = BoundingBoxGUI(mat.get_data())
    selectRegionGUI.run()
    if not selectRegionGUI.bboxes:
        print("No bounding box selected. Exiting.")
        cam.close()
        return
    selectRegionROI = selectRegionGUI.bboxes[0]

    # Create and set mask ROI in the camera
    print("Setting region of interest mask in the camera")
    img_mask = sl.Mat(image_size_dense.width, image_size_dense.height, sl.MAT_TYPE.U8_C1)
    img_mask.set_to(0)
    for i in range(selectRegionROI[0], selectRegionROI[0] + selectRegionROI[2]):
        for j in range(selectRegionROI[1], selectRegionROI[1] + selectRegionROI[3]):
            img_mask.set_value(i, j, 1)
    cam.set_region_of_interest(img_mask)

    # Crop the image to the selected ROI
    img_crop = mat.get_data()[selectRegionROI[1]:selectRegionROI[1] + selectRegionROI[3],
                             selectRegionROI[0]:selectRegionROI[0] + selectRegionROI[2], :]

    # Optionally run SAM segmentation on the cropped image
    ifUseSAM = input("Use SAM to segment the image? (T/F) ").upper()
    sam_gui = None
    if ifUseSAM == "T":
        reSelect_sam = False
        while not reSelect_sam:
            # Path to SAM model checkpoint (adjust as needed)
            sam_checkpoint = r".\sam_vit_h_4b8939.pth"
            if not os.path.exists(sam_checkpoint):
                raise FileNotFoundError(f"SAM model checkpoint not found at {sam_checkpoint}. Please download it.")

            sam_model = sam_model_registry["vit_h"](checkpoint=sam_checkpoint)
            sam_gui = SegmentAnythingGUI(mat.get_data(), sam_model)
            sam_gui.run()

            # Save the segmentation mask points
            reSelect_sam = save_data(cam, dense_point_cloud, image_size_dense,
                                     sam_gui.mask_coordinates, filepath, frame_id, "SAM")

    # Select fiducial points interactively
    ifSelectFids = input("Select fiducials? (T/F) ").upper()
    if ifSelectFids == "T":
        reSelect = False
        while not reSelect:
            reSelect = selectPointsBorder(img_crop, cam, selectRegionROI, dense_point_cloud,
                                         image_size_dense, filepath, "fids", frame_id,
                                         sam_gui.mask_coordinates if sam_gui else [])

    # Select target points interactively
    ifSelectTgts = input("Select target points? (T/F) ").upper()
    if ifSelectTgts == "T":
        reSelect = False
        while not reSelect:
            reSelect = selectPointsBorder(img_crop, cam, selectRegionROI, dense_point_cloud,
                                         image_size_dense, filepath, "tgt", frame_id,
                                         sam_gui.mask_coordinates if sam_gui else [])

    # Select border points interactively
    ifSelectBorder = input("Select border? (T/F) ").upper()
    if ifSelectBorder == "T":
        selectPointsBorder(img_crop, cam, selectRegionROI, dense_point_cloud,
                           image_size_dense, filepath, "border", frame_id)

    # Select arUco fiducial points interactively
    ifSelectAfids = input("Select arUco fiducials? (T/F) ").upper()
    if ifSelectAfids == "T":
        reSelect = False
        while not reSelect:
            reSelect = selectPointsBorder(mat.get_data(), cam, selectRegionROI, dense_point_cloud,
                                         image_size_dense, filepath, "arUco", frame_id,
                                         sam_gui.mask_coordinates if sam_gui else [])

    # Save the whole ROI point cloud
    roi_list = []
    for i in range(selectRegionROI[0], selectRegionROI[0] + selectRegionROI[2]):
        for j in range(selectRegionROI[1], selectRegionROI[1] + selectRegionROI[3]):
            roi_list.append((i, j))

    save_data(cam, dense_point_cloud, image_size_dense, roi_list, filepath, frame_id, "PC")

    cam.close()


def select_frame(filepath):
    """
    Allow user to browse frames in an SVO file and select one interactively.

    Args:
        filepath (str): path to SVO file

    Returns:
        int: selected frame id
    """
    input_type = sl.InputType()
    input_type.set_from_svo_file(filepath)
    init = sl.InitParameters(input_t=input_type,
                             depth_mode=sl.DEPTH_MODE.NEURAL,
                             coordinate_units=sl.UNIT.METER)
    cam = sl.Camera()
    status = cam.open(init)
    if status != sl.ERROR_CODE.SUCCESS:
        print(f"Failed to open camera: {repr(status)}")
        exit()

    total_frames = cam.get_svo_number_of_frames()
    print(f"Total frames in SVO: {total_frames}")

    frame_id = 0

    while True:
        cam.set_svo_position(frame_id)
        if cam.grab() == sl.ERROR_CODE.SUCCESS:
            mat = sl.Mat(cam.get_camera_information().camera_configuration.resolution.width,
                         cam.get_camera_information().camera_configuration.resolution.height,
                         sl.MAT_TYPE.F32_C4)
            cam.retrieve_image(mat, sl.VIEW.LEFT)
            cv2_image = mat.get_data()

            cv2.namedWindow("image", cv2.WINDOW_KEEPRATIO)
            cv2.imshow("image", cv2_image)
            key = cv2.waitKey(0)
            if key == ord('l'):  # previous frame
                frame_id = max(frame_id - 1, 0)
            elif key == ord('r'):  # next frame
                frame_id = min(frame_id + 1, total_frames - 1)
            elif key == ord('q'):  # quit and select current frame
                break
        else:
            print("No image data available.")

    cv2.destroyAllWindows()
    cam.close()
    return frame_id
