import cv2
import numpy as np
from segment_anything import SamPredictor

class SegmentAnythingGUI:
    def __init__(self, image, sam_model):
        self.image = image.copy()
        self.orig_image = image.copy()

        # Zoom-related variables
        self.zoom_level = 1.0
        self.zoom_step = 0.1
        self.pan_start = None
        self.offset = [0, 0]

        print(f"Original image size: {self.image.shape}")

        # Store the original image size
        self.orig_h, self.orig_w = self.image.shape[:2]

        # Resize the image for SAM
        self.image = self.resize_image_long_side(self.image, 1024)
        print(f"Resized image size: {self.image.shape}")

        # Store the resized image size
        self.resized_h, self.resized_w = self.image.shape[:2]

        self.sam_predictor = SamPredictor(sam_model)
        self.sam_predictor.set_image(self.image)

        self.foreground_pts = np.empty((0, 2))  # Foreground points
        self.background_pts = np.empty((0, 2))  # Background points
        self.current_inputpts = None

        self.current_mask = None
        self.mask_coordinates = []  # Stores the coordinates of mask=1 regions in original resolution
        cv2.namedWindow('image', cv2.WINDOW_KEEPRATIO | cv2.WINDOW_GUI_NORMAL)
        cv2.setMouseCallback('image', self.mouse_callback)

    def resize_image_long_side(self, image, target_size):
        if image.shape[2] == 4:
            image = cv2.cvtColor(image, cv2.COLOR_RGBA2RGB)

        h, w = image.shape[:2]
        if max(h, w) > target_size:
            scale = target_size / max(h, w)
            new_h, new_w = int(h * scale), int(w * scale)
            image = cv2.resize(image, (new_w, new_h))
        return image

    def mouse_callback(self, event, x, y, flags, params):
        # Adjust coordinates for zoom/pan
        adj_x = int((x + self.offset[0]) / self.zoom_level)
        adj_y = int((y + self.offset[1]) / self.zoom_level)
        
        # Panning with middle mouse button
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
        elif event == cv2.EVENT_LBUTTONDOWN:
            self.current_inputpts = [adj_x, adj_y]
        elif event == cv2.EVENT_LBUTTONUP:
            self.foreground_pts = np.vstack([self.foreground_pts, self.current_inputpts])
            self.current_inputpts = None
            self.generate_mask()
        elif event == cv2.EVENT_RBUTTONDOWN:
            self.current_inputpts = [adj_x, adj_y]
        elif event == cv2.EVENT_RBUTTONUP:
            self.background_pts = np.vstack([self.background_pts, self.current_inputpts])
            self.current_inputpts = None
            self.generate_mask()
        elif event == cv2.EVENT_MOUSEMOVE and flags & cv2.EVENT_FLAG_CTRLKEY:
            if self.current_mask is not None and 0 <= adj_x < self.current_mask.shape[1] and 0 <= adj_y < self.current_mask.shape[0]:
                radius = int(5 / self.zoom_level)  # Scale brush size with zoom
                for i in range(-radius, radius + 1):
                    for j in range(-radius, radius + 1):
                        nx, ny = adj_x + i, adj_y + j
                        if 0 <= nx < self.current_mask.shape[1] and 0 <= ny < self.current_mask.shape[0]:
                            self.current_mask[ny, nx] = 1
                self.store_mask_coordinates()
                self.draw_masks()
        elif event == cv2.EVENT_MOUSEMOVE and flags & cv2.EVENT_FLAG_ALTKEY:
            if self.current_mask is not None and 0 <= adj_x < self.current_mask.shape[1] and 0 <= adj_y < self.current_mask.shape[0]:
                radius = int(5 / self.zoom_level)  # Scale brush size with zoom
                for i in range(-radius, radius + 1):
                    for j in range(-radius, radius + 1):
                        nx, ny = adj_x + i, adj_y + j
                        if 0 <= nx < self.current_mask.shape[1] and 0 <= ny < self.current_mask.shape[0]:
                            self.current_mask[ny, nx] = 0
                self.store_mask_coordinates()
                self.draw_masks()

    def generate_mask(self):
        # Combine foreground and background points
        input_point = np.vstack([self.foreground_pts, self.background_pts])
        input_label = np.hstack([
            np.ones(len(self.foreground_pts)),  # Foreground labels (1)
            np.zeros(len(self.background_pts))  # Background labels (0)
        ])

        # Predict masks
        masks, scores, _ = self.sam_predictor.predict(
            point_coords=input_point,
            point_labels=input_label,
            multimask_output=True,
        )
        self.current_mask = masks[np.argmax(scores)]

        # Extract and store the coordinates of mask=1 regions in original resolution
        self.store_mask_coordinates()

        self.draw_masks()

    def store_mask_coordinates(self):
        if self.current_mask is not None:
            # Resize the mask back to the original image size
            mask_resized = cv2.resize(self.current_mask.astype(np.uint8), (self.orig_w, self.orig_h), interpolation=cv2.INTER_NEAREST)

            # Get the coordinates where mask=1
            y_coords, x_coords = np.where(mask_resized == 1)

            # 清空之前的坐标并存储新的坐标
            self.mask_coordinates = list(zip(x_coords, y_coords))

    def draw_masks(self):
        display_image = self.image.copy()
        
        if self.current_mask is not None:
            mask_resized = cv2.resize(self.current_mask.astype(np.uint8), 
                                    (self.image.shape[1], self.image.shape[0]), 
                                    interpolation=cv2.INTER_NEAREST)
            mask_colored = np.zeros_like(self.image, dtype=np.uint8)
            mask_colored[mask_resized > 0] = np.array([255, 144, 30], dtype=np.uint8)
            display_image = cv2.addWeighted(display_image, 1.0, mask_colored, 0.6, 0)

            for pt in self.foreground_pts:
                cv2.circle(display_image, (int(pt[0]), int(pt[1])), 5, (0, 0, 255), -1)
            for pt in self.background_pts:
                cv2.circle(display_image, (int(pt[0]), int(pt[1])), 5, (0, 255, 0), -1)
        
        # Apply zoom and pan transformations
        if self.zoom_level != 1.0:
            h, w = display_image.shape[:2]
            new_w, new_h = int(w * self.zoom_level), int(h * self.zoom_level)
            zoomed_img = cv2.resize(display_image, (new_w, new_h))
            
            # Calculate crop area based on offset
            x1 = max(0, self.offset[0])
            y1 = max(0, self.offset[1])
            x2 = min(new_w, x1 + self.resized_w)
            y2 = min(new_h, y1 + self.resized_h)
            
            if x2 > x1 and y2 > y1:
                display_image = zoomed_img[y1:y2, x1:x2]
            else:
                # If we're panned beyond image bounds, show black border
                display_image = np.zeros_like(self.image)
        
        cv2.imshow('image', display_image)

    def run(self):
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
            elif key == ord('+') or key == ord('='):  # Zoom in
                self.zoom_level += self.zoom_step
                self.draw_masks()
            elif key == ord('-') or key == ord('_'):  # Zoom out
                self.zoom_level = max(1.0, self.zoom_level - self.zoom_step)
                self.offset = [0, 0]  # Reset offset when zooming out
                self.draw_masks()
            elif key == ord('0'):  # Reset zoom
                self.zoom_level = 1.0
                self.offset = [0, 0]
                self.draw_masks()
                
        cv2.destroyAllWindows()

class BoundingBoxGUI:
    def __init__(self, image):
        self.image = image.copy()
        self.orig_image = image.copy()
        self.bboxes = []
        self.current_box = None
        self.mouse_down = False
        cv2.namedWindow('image', cv2.WINDOW_KEEPRATIO)
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
            # left up coord, right down coord, rec color, line width
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
        self.mouse_down = False
        self.draw_bolder = False

        cv2.namedWindow('image', cv2.WINDOW_KEEPRATIO)
        cv2.setMouseCallback('image', self.mouse_callback)

    def mouse_callback(self, event, x, y, flags, params):
        if event == cv2.EVENT_MOUSEMOVE and flags & cv2.EVENT_FLAG_CTRLKEY:
            self.current_centroid = (x, y)
            self.centroids.append(self.current_centroid)
            self.current_centroid = None
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
                    self.draw_centroids()
        elif event == cv2.EVENT_MOUSEMOVE and flags & cv2.EVENT_FLAG_ALTKEY:
            for centroids in self.centroids:
                if centroids[0] - 7 <= x <= centroids[0] + 7 and centroids[1] - 7 <= y <= centroids[1] + 7:
                    self.centroids.remove(centroids)
                    self.draw_centroids()

    def draw_centroids(self):
        for centroid in self.centroids:
            cv2.circle(self.image, (centroid[0], centroid[1]), 3, (0, 255, 0), 2)

    def run(self):
        while True:
            self.image = self.orig_image.copy()
            self.draw_centroids()
            cv2.imshow('image', self.image)

            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('d'):
                if len(self.centroids) > 0:
                    self.centroids.pop()

        cv2.destroyAllWindows()