from concurrent.futures import Executor, ThreadPoolExecutor, as_completed
import time
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
from backend.services.ml.frame import FastFrameFinder
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
        finder = FastFrameFinder()
        save_directory = 'backend/services/video/bestframes/'

        start_time = time.time()
        frame = []
        with ThreadPoolExecutor(max_workers=3) as executor:
            future_to_video = {
                executor.submit(finder.process_video, video, save_directory): video
                for video in videos
            }
            for future in as_completed(future_to_video):
                video = future_to_video[future]
                try:
                    result = future.result()
                    if isinstance(result, str):
                        frame.append(result)
                    print(
                        f"Processing completed for {video}: {'Frame found' if isinstance(result, str) else 'No frame found'}"
                    )
                except Exception as exc:
                    print(f"Processing for {video} generated an exception: {exc}")

        end_time = time.time()
        print(f"Total processing time: {end_time - start_time:.2f} seconds")
        MLOCR = ImageProcessor(r'C:/Program Files/Tesseract-OCR/tesseract.exe', frame).process_images()
        MLFRESH = ImageProcessor(r'C:/Program Files/Tesseract-OCR/tesseract.exe', frame).predict_image()
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
                                    result=[ProductSchema.from_sqlalchemy(obj)]
                )

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        await websocket.send_text(str(self.id))
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
 
    async def process_somethings(self, video_path:list[str]):
         await self.process_video(video_path)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)