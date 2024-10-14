import uuid
from fastapi import Depends
from fastapi import WebSocket
from backend.commons.responses import ServiceResponse, ServiceResponseStatus
from backend.db.models.product import Product
from backend.logging import get_logger
from backend.schemas.product import ProductSchema
from backend.services.base.crud import FormService
from backend.services.commons.base import BaseService
import cv2
import numpy as np
from PIL import Image
import os
from backend.db.dependencies import get_db_session
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
import tensorflow as tf
import keras as ks
from keras.api.applications import MobileNetV2
from backend.services.ml.crud import ImageProcessor
logger = get_logger(__name__)


class LiveFeed(BaseService):
    __item_name__ = "FormService"

    def __init__(self):
        self.id = uuid.uuid4()
        self.model = MobileNetV2(weights='imagenet')
        self.active_connections: list[WebSocket] = []
    
    def preprocess_image(self, image):
        image = cv2.resize(image, (224, 224))
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        image = tf.keras.applications.mobilenet_v2.preprocess_input(image)
        return image

    def is_vegetable_or_packaged_product(self, class_name):
        vegetables = ['vegetable', 'fruit', 'produce','spaghetti_squash']
        packaged_products = ['package', 'box', 'container','pop_bottle','laptop','sunscreen','modem','lotion','oil_filter','sunscreen','hard_disc','carton']
        return any(item in class_name.lower() for item in vegetables + packaged_products)

    def detect_object(self, image):
        preprocessed_image = self.preprocess_image(image)
        predictions = self.model(np.expand_dims(preprocessed_image, axis=0))
        decoded_predictions = ks.applications.mobilenet_v2.decode_predictions(predictions.numpy(), top=1)[0]
        class_name = decoded_predictions[0][1]
        confidence = decoded_predictions[0][2]
        return class_name, confidence

    def is_perfect_image(self, image, class_name, confidence, threshold=0.8):
        height, width = image.shape[:2]
        center_y, center_x = height // 2, width // 2
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if contours:
            largest_contour = max(contours, key=cv2.contourArea)
            x, y, w, h = cv2.boundingRect(largest_contour)
            is_centered = abs(center_x - (x + w // 2)) < width * 0.1 and abs(center_y - (y + h // 2)) < height * 0.1
            is_large_enough = (w * h) / (width * height) > 0.4
            return is_centered and is_large_enough and confidence > threshold
        return False

    async def process_video(self, video_path ,db):
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            print(f"Error: Could not open video file {video_path}")
            return

        # Define the directory to save the image
        save_directory = 'backend/services/video/bestframes/'  # Change this to your desired directory
        if not os.path.exists(save_directory):
            os.makedirs(save_directory)

        # Initialize variables to track the highest confidence and corresponding frame
        highest_confidence = 0.0
        best_frame = None
        best_class_name = None
        best_frame_count = None

        frame_count = 0
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
            
            frame_count += 1
            class_name, confidence = self.detect_object(frame)
            # import pdb
            # pdb.set_trace()
            # Check if the current class is a vegetable or packaged product, or if the image is perfect
            if self.is_vegetable_or_packaged_product(class_name) or self.is_perfect_image(frame, class_name, confidence):
                print(f"Perfect image found in frame {frame_count}: {class_name} (Confidence: {confidence:.2f})")
                # Update if the current confidence is the highest so far
                if confidence > highest_confidence:
                    highest_confidence = confidence
                    best_frame = frame
                    best_class_name = class_name
                    best_frame_count = frame_count

        # Save the best frame only if it was updated
        if best_frame is not None:
            image_filename = f"perfect_{best_class_name}_{highest_confidence:.2f}_frame_{best_frame_count}.jpg"
            cv2.imwrite(os.path.join(save_directory, image_filename), best_frame)
            print(f"Saved image: {image_filename} with confidence: {highest_confidence:.2f}")
            MLOCR = ImageProcessor(r'C:/Program Files/Tesseract-OCR/tesseract.exe', save_directory+image_filename).process_image()
            MLFRESH = ImageProcessor(r'C:/Program Files/Tesseract-OCR/tesseract.exe', save_directory+image_filename).predict_image()
            obj = ProductSchema(
                name=MLOCR["name"],
                expiry_date=MLOCR["expiry_date"],
                manufacturing_date=MLOCR.get("manufacturing_date"),  # Use .get() in case the key is missing
                mrp=MLOCR["mrp"],
                description=MLFRESH.get("Predicted Class")
            )
            service = FormService(db)
            await service.createProductListing(obj)
            return self.response(ServiceResponseStatus.FETCHED,
                                 result=[MLOCR,MLFRESH]
            )
        else:
            print("No suitable image found to save.")

        cap.release()
        cv2.destroyAllWindows()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        video_path = f"backend/services/video/{self.id}.mkv"
        # await websocket.send_text(self.id)
        try:
            with open(video_path, "wb") as video_file:
                while True:
                    try:
                        print("Receiving data")
                        data = await websocket.receive_bytes()
                        if not data:
                            print("data null")
                            break 
                        print("recived data")
                        video_file.write(data)
                        print("data written")
                    except Exception as e:
                        print(f"Error receiving data: {e}")
                        await websocket.send_text(self.id)
                        break
        except Exception as e:
            print(f"File handling error: {e}")
 
    async def process_somethings(self, video_path:str):
         await self.process_video(video_path)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)