import base64
import json
import os
import time
import uuid
from fastapi import Depends
from fastapi import WebSocket
from backend.commons.responses import ServiceResponseStatus
from backend.logging import get_logger
from backend.schemas.product import ProductSchema
from backend.services.base.crud import FormService
from backend.services.commons.base import BaseService
from backend.services.ml.frame import ObjectDetectionVideoProcessor
from keras.api.applications import MobileNetV2
from backend.services.ml.crud import ImageProcessor
logger = get_logger(__name__)


class LiveFeed(BaseService):
    __item_name__ = "FormService"

    def __init__(self):
        self.id = uuid.uuid4()
        self.model = MobileNetV2(weights='imagenet')
        self.active_connections: list[WebSocket] = []
    

    async def process_video(self, videos ,db):
        save_directory = 'backend/services/video/bestframes/'
        processor = ObjectDetectionVideoProcessor(save_directory)
        saved_frames = processor.process_videos(videos)
        print(saved_frames)
        MLOCR = ImageProcessor(r'C:/Program Files/Tesseract-OCR/tesseract.exe', saved_frames).process_images()
        MLFRESH = ImageProcessor(r'C:/Program Files/Tesseract-OCR/tesseract.exe', saved_frames).predict_image()
        print(MLFRESH)
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
                                    result=[{**MLOCR, **MLFRESH}]
                )

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        await websocket.send_text(str(self.id))
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        image_list = []  # List to hold the paths of saved images
        image_count = 0  # Counter for unique image filenames
        image_dir = 'backend/services/video/images/'

        # Create the directory if it doesn't exist
        if not os.path.exists(image_dir):
            os.makedirs(image_dir)
        try:
            prev =""
            while True:
                try:
                    # Receive JSON data
                    data = await websocket.receive_text()
                    
                    if not data:
                        print("No data received, exiting loop")
                        break 

                    json_data = json.loads(data)  # Parse the received JSON

                    # Extract image and class data
                    image_base64 = json_data.get('image')
                    detected_class = json_data.get('class')
                    
                    if image_base64:
                        image_data = base64.b64decode(image_base64.split(",")[1])

                        image_filename = f"backend/services/video/images/{self.id}_image_{detected_class}_{image_count}.jpg"
                        if detected_class != prev:
                            print("Enterned here")
                            image_list.append(image_filename)

                            with open(image_filename, "wb") as image_file:
                                image_file.write(image_data)
                            
                            print(f"Image saved: {image_filename}")
                            image_count += 1
                    if image_count >= 20 and detected_class != prev:
                        image_count=0
                        prev = detected_class
                        print(detected_class,prev,":---------------bigleu was here")
                        await websocket.send_json({"img": image_list})
                        image_list.clear()
                except Exception as e:
                    print(f"Error receiving or processing data: {e}")
                    await websocket.send_text(f"Error: {str(e)}")
                    break
        except Exception as e:
            print(f"File handling error: {e}")

        # Optionally send the list of saved images back to the client


 
    async def process_somethings(self,db, video_path:list[str]):
        MLOCR = ImageProcessor(r'C:/Program Files/Tesseract-OCR/tesseract.exe', video_path).process_images()
        MLFRESH = ImageProcessor(r'C:/Program Files/Tesseract-OCR/tesseract.exe', video_path).predict_best_image(video_path)
        print(MLFRESH)
        obj = ProductSchema(
                    name=MLOCR["name"],
                    expiry_date=MLOCR["expiry_date"],
                    manufacturing_date=MLOCR.get("manufacturing_date"),
                    mrp=MLOCR["mrp"],
                    description=MLFRESH.get("Predicted Class")
                )
        service = FormService(db)
        await service.createProductListing(obj)
        return self.response(ServiceResponseStatus.FETCHED,
                                    result=[{**MLOCR, **MLFRESH}]
                )

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)