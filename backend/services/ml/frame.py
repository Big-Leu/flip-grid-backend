import cv2
import numpy as np
import os
import tensorflow as tf
from keras.api.applications import MobileNetV2
import keras as ks
from concurrent.futures import ThreadPoolExecutor, as_completed
import time


class FastFrameFinder:
    def __init__(self):
        self.model = MobileNetV2(weights="imagenet")

    def preprocess_image(self, image):
        image = cv2.resize(image, (224, 224))
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        image = tf.keras.applications.mobilenet_v2.preprocess_input(image)
        return image

    def is_target_object(self, class_name):
        target_objects = set(
            [
                "vegetable",
                "fruit",
                "produce",
                "spaghetti_squash",
                "package",
                "box",
                "container",
                "pop_bottle",
                "laptop",
                "sunscreen",
                "modem",
                "lotion",
                "oil_filter",
                "hard_disc",
                "carton",
            ]
        )
        return any(item in class_name.lower() for item in target_objects)

    def detect_object(self, image):
        preprocessed_image = self.preprocess_image(image)
        predictions = self.model(np.expand_dims(preprocessed_image, axis=0))
        decoded_predictions = ks.applications.mobilenet_v2.decode_predictions(
            predictions.numpy(), top=1
        )[0]
        class_name = decoded_predictions[0][1]
        confidence = decoded_predictions[0][2]
        return class_name, confidence

    def calculate_frame_score(self, frame, class_name, confidence):
        height, width = frame.shape[:2]
        center_y, center_x = height // 2, width // 2

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

        contours, _ = cv2.findContours(
            binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )

        if contours:
            largest_contour = max(contours, key=cv2.contourArea)
            x, y, w, h = cv2.boundingRect(largest_contour)

            centering_score = (
                1
                - (
                    abs(center_x - (x + w // 2)) / width
                    + abs(center_y - (y + h // 2)) / height
                )
                / 2
            )

            size_score = (w * h) / (width * height)

            return (0.4 * confidence + 0.3 * centering_score + 0.3 * size_score) * 100

        return 0

    def crop_and_rotate(self, frame):
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

        contours, _ = cv2.findContours(
            binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )

        if contours:
            largest_contour = max(contours, key=cv2.contourArea)
            x, y, w, h = cv2.boundingRect(largest_contour)

            padding = 20
            x = max(0, x - padding)
            y = max(0, y - padding)
            w = min(frame.shape[1] - x, w + 2 * padding)
            h = min(frame.shape[0] - y, h + 2 * padding)

            cropped_frame = frame[y : y + h, x : x + w]
            return cropped_frame

        return frame

    def find_good_frame(self, video_path, save_directory):
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            print(f"Error: Could not open video file {video_path}")
            return False

        if not os.path.exists(save_directory):
            os.makedirs(save_directory)

        frame_count = 0
        list = []
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            frame_count += 1
            class_name, confidence = self.detect_object(frame)
            if self.is_target_object(class_name):
                frame_score = self.calculate_frame_score(frame, class_name, confidence)

                if frame_score > 50:
                    print(
                        f"Good frame found in {video_path}: Frame {frame_count}, {class_name}, Score: {frame_score:.2f}"
                    )

                    processed_frame = self.crop_and_rotate(frame)

                    image_filename = f"good_{os.path.basename(video_path)}_{class_name}_{frame_score:.2f}_frame_{frame_count}.jpg"
                    cv2.imwrite(
                        os.path.join(save_directory, image_filename), processed_frame
                    )
                    print(f"Saved good image: {image_filename}")
                    cap.release()
                    cv2.destroyAllWindows()
                    return save_directory+image_filename

        cap.release()
        cv2.destroyAllWindows()
        print(f"No suitable frames found in {video_path}")
        return False


    def process_video(self,video, save_directory):
        return self.find_good_frame(video, save_directory)



