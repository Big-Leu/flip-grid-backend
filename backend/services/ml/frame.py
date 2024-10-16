import cv2
import torch
import os
import uuid  # Import uuid for generating unique identifiers


class ObjectDetectionVideoProcessor:
    def __init__(self, output_dir, model_name="yolov5s"):
        self.model = torch.hub.load("ultralytics/yolov5", model_name)
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

    def process_videos(self, video_paths):
        saved_frame_paths = []  # List to hold paths of saved frames
        for video_path in video_paths:
            saved_frames = self.process_video(video_path)
            saved_frame_paths.extend(saved_frames)  # Extend the list with saved frames from this video
        return saved_frame_paths

    def process_video(self, video_path):
        saved_frames = []  # List to hold saved frames for the current video
        cap = cv2.VideoCapture(video_path)
        frame_count = 0  # Track frame number

        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                print(f"Finished processing video: {video_path}")
                break

            frame_count += 1

            # Perform object detection on the frame
            results = self.model(frame)
            detected_objects = results.pandas().xyxy[0]  # Bounding boxes and labels in a Pandas DataFrame

            # Check if any object was detected
            if len(detected_objects) > 0:
                # Get the names of detected objects
                object_names = detected_objects["name"].unique()  # Unique object names detected
                object_names_str = "_".join(object_names)  # Join them into a string for filename

                # Generate a unique filename using uuid
                unique_id = uuid.uuid4()  # Create a unique identifier
                output_frame_path = os.path.join(
                    self.output_dir,
                    f"frame_with_objects_{frame_count}_{object_names_str}_{unique_id}.jpg",
                )
                cv2.imwrite(output_frame_path, frame)
                saved_frames.append(output_frame_path)  # Append the saved frame path to the list

                print(
                    f"Frame {frame_count} saved from {video_path} with {len(detected_objects)} detected objects: {object_names_str}"
                )
                break

        cap.release()
        cv2.destroyAllWindows()
        return saved_frames  # Return the list of saved frame paths