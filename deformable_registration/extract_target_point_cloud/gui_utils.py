import cv2
import numpy as np
from segment_anything import SamPredictor

class SegmentAnythingGUI:
    """
    Interactive GUI for segmenting an image using the Segment Anything Model (SAM).
    
    Features:
    - Interactive point-based mask creation
    - Foreground/background selection
    - Mask editing with brush tools
    - Zoom and pan for better inspection
    - Stores mask coordinates in the original image resolution
    """

    def __init__(self, image, sam_model):
        """
        Initializes the segmentation GUI with an input image and a SAM model.

        Args:
            image (np.ndarray): Input RGB image
            sam_model: Pre-loaded SAM model instance
        """
        self.image = image.copy()
        self.orig_image = image.copy()

        # For zoom & pan functionality
        self.zoom_level = 1.0
        self.zoom_step = 0.1
        self.pan_start = None
        self.offset = [0, 0]

        print(f"Original image size: {self.image.shape}")

        # Save original size for coordinate mapping
        self.orig_h, self.orig_w = self.image.shape[:2]

        # Resize the image to fit the SAM model's input requirements
        self.image = self.resize_image_long_side(self.image, 1024)
        print(f"Resized image size: {self.image.shape}")
        self.resized_h, self.resized_w = self.image.shape[:2]

        # Initialize SAM predictor
        self.sam_predictor = SamPredictor(sam_model)
        self.sam_predictor.set_image(self.image)

        # Interactive points
        self.foreground_pts = np.empty((0, 2))
        self.background_pts = np.empty((0, 2))
        self.current_inputpts = None

        # Current predicted mask
        self.current_mask = None
        self.mask_coordinates = []  # Stores mask=1 coords in original image resolution

        # Setup OpenCV window and mouse callback
        cv2.namedWindow('image', cv2.WINDOW_KEEPRATIO | cv2.WINDOW_GUI_NORMAL)
        cv2.setMouseCallback('image', self.mouse_callback)

    def resize_image_long_side(self, image, target_size):
        """
        Resizes the input image so its longest side equals target_size, preserving aspect ratio.

        Args:
            image (np.ndarray): input image
            target_size (int): size of the longest side

        Returns:
            np.ndarray: resized image
        """
        if image.shape[2] == 4:
            image = cv2.cvtColor(image, cv2.COLOR_RGBA2RGB)

        h, w = image.shape[:2]
        if max(h, w) > target_size:
            scale = target_size / max(h, w)
            new_h, new_w = int(h * scale), int(w * scale)
            image = cv2.resize(image, (new_w, new_h))
        return image

    def mouse_callback(self, event, x, y, flags, params):
        """
        Handles all mouse events including:
        - adding points
        - panning
        - mask editing with brush (ctrl/alt + mouse)
        """
        # Map display coordinates to image coordinates, considering zoom/pan
        adj_x = int((x + self.offset[0]) / self.zoom_level)
        adj_y = int((y + self.offset[1]) / self.zoom_level)

        # Pan start
        if event == cv2.EVENT_MBUTTONDOWN:
            self.pan_start = (x, y)
        elif event == cv2.EVENT_MOUSEMOVE and flags & cv2.EVENT_FLAG_MBUTTON:
            if self.pan_start:
                dx = x - self.pan_start[0]
                dy = y - self.pan_start[1]
                self.offset[0] -= dx
                self.offset[1] -= dy
                self.pan_start = (x, y)
                self.draw_masks()
        elif event == cv2.EVENT_MBUTTONUP:
            self.pan_start = None

        # Left click: foreground point
        elif event == cv2.EVENT_LBUTTONDOWN:
            self.current_inputpts = [adj_x, adj_y]
        elif event == cv2.EVENT_LBUTTONUP:
            self.foreground_pts = np.vstack([self.foreground_pts, self.current_inputpts])
            self.current_inputpts = None
            self.generate_mask()

        # Right click: background point
        elif event == cv2.EVENT_RBUTTONDOWN:
            self.current_inputpts = [adj_x, adj_y]
        elif event == cv2.EVENT_RBUTTONUP:
            self.background_pts = np.vstack([self.background_pts, self.current_inputpts])
            self.current_inputpts = None
            self.generate_mask()

        # Brush to add to mask (ctrl+move)
        elif event == cv2.EVENT_MOUSEMOVE and flags & cv2.EVENT_FLAG_CTRLKEY:
            if self.current_mask is not None and 0 <= adj_x < self.current_mask.shape[1] and 0 <= adj_y < self.current_mask.shape[0]:
                radius = int(5 / self.zoom_level)
                for i in range(-radius, radius + 1):
                    for j in range(-radius, radius + 1):
                        nx, ny = adj_x + i, adj_y + j
                        if 0 <= nx < self.current_mask.shape[1] and 0 <= ny < self.current_mask.shape[0]:
                            self.current_mask[ny, nx] = 1
                self.store_mask_coordinates()
                self.draw_masks()
        # Brush to remove from mask (alt+move)
        elif event == cv2.EVENT_MOUSEMOVE and flags & cv2.EVENT_FLAG_ALTKEY:
            if self.current_mask is not None and 0 <= adj_x < self.current_mask.shape[1] and 0 <= adj_y < self.current_mask.shape[0]:
                radius = int(5 / self.zoom_level)
                for i in range(-radius, radius + 1):
                    for j in range(-radius, radius + 1):
                        nx, ny = adj_x + i, adj_y + j
                        if 0 <= nx < self.current_mask.shape[1] and 0 <= ny < self.current_mask.shape[0]:
                            self.current_mask[ny, nx] = 0
                self.store_mask_coordinates()
                self.draw_masks()

    def generate_mask(self):
        """
        Uses SAM to predict a mask based on current foreground and background points.
        """
        input_point = np.vstack([self.foreground_pts, self.background_pts])
        input_label = np.hstack([
            np.ones(len(self.foreground_pts)),
            np.zeros(len(self.background_pts)),
        ])

        masks, scores, _ = self.sam_predictor.predict(
            point_coords=input_point,
            point_labels=input_label,
            multimask_output=True,
        )

        self.current_mask = masks[np.argmax(scores)]
        self.store_mask_coordinates()
        self.draw_masks()

    def store_mask_coordinates(self):
        """
        Converts the current mask to coordinates in the original image size.
        """
        if self.current_mask is not None:
            mask_resized = cv2.resize(
                self.current_mask.astype(np.uint8),
                (self.orig_w, self.orig_h),
                interpolation=cv2.INTER_NEAREST
            )
            y_coords, x_coords = np.where(mask_resized == 1)
            self.mask_coordinates = list(zip(x_coords, y_coords))

    def draw_masks(self):
        """
        Draws the current mask overlay + user-provided points + zoom/pan.
        """
        display_image = self.image.copy()
        
        if self.current_mask is not None:
            # Draw mask in orange
            mask_resized = cv2.resize(
                self.current_mask.astype(np.uint8),
                (self.image.shape[1], self.image.shape[0]),
                interpolation=cv2.INTER_NEAREST
            )
            mask_colored = np.zeros_like(self.image, dtype=np.uint8)
            mask_colored[mask_resized > 0] = np.array([255, 144, 30], dtype=np.uint8)
            display_image = cv2.addWeighted(display_image, 1.0, mask_colored, 0.6, 0)

            # Foreground points in red, background in green
            for pt in self.foreground_pts:
                cv2.circle(display_image, (int(pt[0]), int(pt[1])), 5, (0, 0, 255), -1)
            for pt in self.background_pts:
                cv2.circle(display_image, (int(pt[0]), int(pt[1])), 5, (0, 255, 0), -1)
        
        # Apply zoom/pan
        if self.zoom_level != 1.0:
            h, w = display_image.shape[:2]
            new_w, new_h = int(w * self.zoom_level), int(h * self.zoom_level)
            zoomed_img = cv2.resize(display_image, (new_w, new_h))
            
            x1 = max(0, self.offset[0])
            y1 = max(0, self.offset[1])
            x2 = min(new_w, x1 + self.resized_w)
            y2 = min(new_h, y1 + self.resized_h)
            
            if x2 > x1 and y2 > y1:
                display_image = zoomed_img[y1:y2, x1:x2]
            else:
                display_image = np.zeros_like(self.image)
        
        cv2.imshow('image', display_image)

    def run(self):
        """
        Event loop for the GUI.
        - q : quit
        - c : clear points and mask
        - + / = : zoom in
        - - / _ : zoom out
        - 0 : reset zoom
        """
        while True:
            self.draw_masks()
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('c'):
                self.foreground_pts = np.empty((0, 2))
                self.background_pts = np.empty((0, 2))
                self.current_mask = None
                self.mask_coordinates = []
            elif key in (ord('+'), ord('=')):
                self.zoom_level += self.zoom_step
            elif key in (ord('-'), ord('_')):
                self.zoom_level = max(1.0, self.zoom_level - self.zoom_step)
                self.offset = [0, 0]
            elif key == ord('0'):
                self.zoom_level = 1.0
                self.offset = [0, 0]
        cv2.destroyAllWindows()

class BoundingBoxGUI:
    """
    Interactive GUI for selecting rectangular regions (bounding boxes) 
    on an image using the mouse. Supports deleting boxes and live display.
    
    Controls:
    - Left click + drag: draw a bounding box
    - Right click: delete a box under cursor
    - d : remove last drawn box
    - q : quit
    """

    def __init__(self, image):
        """
        Initializes the bounding box GUI.

        Args:
            image (np.ndarray): Input RGB image
        """
        self.image = image.copy()
        self.orig_image = image.copy()
        self.bboxes = []  # List of (x, y, w, h)
        self.current_box = None
        self.mouse_down = False

        cv2.namedWindow('image', cv2.WINDOW_KEEPRATIO)
        cv2.setMouseCallback('image', self.mouse_callback)

    def mouse_callback(self, event, x, y, flags, params):
        """
        Handles mouse events for drawing and deleting bounding boxes.
        """
        if event == cv2.EVENT_LBUTTONDOWN:
            self.mouse_down = True
            self.current_box = (x, y, 0, 0)
        elif event == cv2.EVENT_MOUSEMOVE and self.mouse_down:
            # Update the size of the current box
            w = x - self.current_box[0]
            h = y - self.current_box[1]
            self.current_box = (self.current_box[0], self.current_box[1], w, h)
        elif event == cv2.EVENT_LBUTTONUP:
            self.mouse_down = False
            self.bboxes.append(self.current_box)
            self.current_box = None
        elif event == cv2.EVENT_RBUTTONDOWN:
            # check if clicked inside any existing box to delete it
            for bbox in self.bboxes:
                if (
                    bbox[0] <= x <= bbox[0] + bbox[2]
                    and bbox[1] <= y <= bbox[1] + bbox[3]
                ):
                    self.bboxes.remove(bbox)
                    break

    def draw_boxes(self):
        """
        Draws all current bounding boxes on the image.
        """
        for box in self.bboxes:
            cv2.rectangle(
                self.image,
                (box[0], box[1]),
                (box[0] + box[2], box[1] + box[3]),
                (0, 255, 0),
                2,
            )

    def run(self):
        """
        Event loop for the bounding box GUI.
        """
        while True:
            self.image = self.orig_image.copy()
            self.draw_boxes()
            cv2.imshow('image', self.image)
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('d'):
                if self.bboxes:
                    self.bboxes.pop()
        cv2.destroyAllWindows()

class CorrectDotsGUI:
    """
    Interactive GUI for placing and correcting landmark points (dots) on an image.

    Features:
    - Left click: place a dot
    - Ctrl + move: place multiple dots quickly (brush mode)
    - Alt + move: erase dots in a small region
    - Right click: delete a dot near the cursor
    - d : remove last added dot
    - q : quit
    """

    def __init__(self, image):
        """
        Initializes the dot correction GUI.

        Args:
            image (np.ndarray): Input RGB image
        """
        self.image = image.copy()
        self.orig_image = image.copy()
        self.centroids = []  # list of (x,y) points
        self.current_centroid = None
        self.mouse_down = False

        cv2.namedWindow('image', cv2.WINDOW_KEEPRATIO)
        cv2.setMouseCallback('image', self.mouse_callback)

    def mouse_callback(self, event, x, y, flags, params):
        """
        Handles mouse events for dot placement and deletion.
        """
        # Brush mode for adding points (Ctrl key)
        if event == cv2.EVENT_MOUSEMOVE and flags & cv2.EVENT_FLAG_CTRLKEY:
            self.centroids.append((x, y))

        # Left click start
        elif event == cv2.EVENT_LBUTTONDOWN:
            self.mouse_down = True
            self.current_centroid = (x, y)
        # Left click release
        elif event == cv2.EVENT_LBUTTONUP:
            self.mouse_down = False
            self.centroids.append(self.current_centroid)
            self.current_centroid = None
        # Right click: delete a close-by dot
        elif event == cv2.EVENT_RBUTTONDOWN:
            for centroid in self.centroids:
                if (
                    centroid[0] - 15 <= x <= centroid[0] + 15
                    and centroid[1] - 15 <= y <= centroid[1] + 15
                ):
                    self.centroids.remove(centroid)
                    break
        # Brush mode for removing points (Alt key)
        elif event == cv2.EVENT_MOUSEMOVE and flags & cv2.EVENT_FLAG_ALTKEY:
            for c in self.centroids:
                if (
                    c[0] - 7 <= x <= c[0] + 7
                    and c[1] - 7 <= y <= c[1] + 7
                ):
                    self.centroids.remove(c)
                    break

    def draw_centroids(self):
        """
        Draw all currently placed dots on the image.
        """
        for centroid in self.centroids:
            cv2.circle(self.image, (centroid[0], centroid[1]), 3, (0, 255, 0), 2)

    def run(self):
        """
        Event loop for the dot correction GUI.
        """
        while True:
            self.image = self.orig_image.copy()
            self.draw_centroids()
            cv2.imshow('image', self.image)
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('d'):
                if self.centroids:
                    self.centroids.pop()
        cv2.destroyAllWindows()
