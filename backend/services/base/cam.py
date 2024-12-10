import base64
import json
import os
import time
import uuid
from fastapi import Depends
from fastapi import WebSocket
from backend.commons.responses import ServiceResponseStatus
from backend.logging import get_logger
from backend.schemas.product import ProductSchema, ProductSchema2
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
        self.model = MobileNetV2(weights="imagenet")
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        await websocket.send_text(str(self.id))
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        image_list = []
        image_count = 0
        image_dir = "backend/services/video/images/"

        if not os.path.exists(image_dir):
            os.makedirs(image_dir)
        try:
            prev = ""
            while True:
                try:
                    data = await websocket.receive_text()

                    if not data:
                        print("No data received, exiting loop")
                        break

                    json_data = json.loads(data)

                    image_base64 = json_data.get("image")
                    detected_class = json_data.get("class")

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
                        image_count = 0
                        prev = detected_class
                        print(detected_class, prev, ":---------------bigleu was here")
                        await websocket.send_json({"img": image_list})
                        image_list.clear()
                except Exception as e:
                    print(f"Error receiving or processing data: {e}")
                    await websocket.send_text(f"Error: {str(e)}")
                    break
        except Exception as e:
            print(f"File handling error: {e}")

    def process(self, video_paths: list[str]) -> bool:
        fruit_keywords = ["banana", "apple", "orange", "grape", "mango", "pear"]
        for path in video_paths:
            if any(fruit.lower() in path.lower() for fruit in fruit_keywords):
                return True
        return False

    async def process_somethings(self, db, video_path: list[str]):
        try:
            flag = self.process(video_path)
            service = FormService(db)
            if not flag:
                MLOCR = ImageProcessor(
                    r"C:/Program Files/Tesseract-OCR/tesseract.exe", video_path
                ).process_images()
                if any(
                    key in MLOCR and MLOCR[key]
                    for key in ["name", "expiry_date", "mrp"]
                ):
                    print("Required fields are present, proceed further.")
                    obj = ProductSchema(
                        name=MLOCR["name"],
                        expiry_date=MLOCR["expiry_date"],
                        manufacturing_date=MLOCR.get("manufacturing_date"),
                        mrp=MLOCR["mrp"],
                        description="A PACKAGED PRODUCT",
                    )
                    await service.createProductListing(obj)
                return self.response(
                    ServiceResponseStatus.FETCHED,
                    result=[ProductSchema2.from_sqlalchemy(obj)],
                )
            else:
                MLFRESH = ImageProcessor(
                    r"C:/Program Files/Tesseract-OCR/tesseract.exe", video_path
                ).predict_best_image(video_path)
                print(MLFRESH)
                obj = ProductSchema(
                    freshStatus=MLFRESH["Predicted Class"],
                    expiry_date="1 WEEK",
                    description="FRUITS OR VEGETABLE",
                    confidence=str(
                        list(MLFRESH["Confidence"])[0]
                        if isinstance(MLFRESH["Confidence"], set)
                        else MLFRESH["Confidence"]
                    ),
                )
                if "rotten" not in MLFRESH["Predicted Class"].lower():
                    await service.createProductListing(obj)
                return self.response(
                    ServiceResponseStatus.FETCHED,
                    result=[ProductSchema2.from_sqlalchemy(obj)],
                )
        except Exception as e:
            print("the eror", e)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)
