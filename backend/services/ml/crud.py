import uuid
from backend.schemas.product import PackagedProductSchema
from backend.services.commons.base import BaseService
import pytesseract
import cv2
import numpy as np
import re
from datetime import datetime
from keras.api.preprocessing import image
from keras.api.models import load_model
import boto3
import pandas as pd
from backend.settings import settings


class ImageProcessor(BaseService):
    __item_name__ = "ML_OCR"

    def __init__(self, tesseract_cmd, image_path,count):
        pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
        self.image_paths = image_path
        self.count = count
        self.text = None

        self.class_mapping = {
            0: 'freshapple', 1: 'freshbanana', 2: 'freshguava', 3: 'freshpomegranate', 4: 'freshorange', 
            5: 'partiallyfreshapple', 6: 'partiallyfreshbanana', 7: 'partiallyfreshguava', 
            8: 'partiallyfreshpomegranate', 9: 'partiallyfreshorange', 
            10: 'rottenapple', 11: 'rottenbanana', 12: 'rottenguava', 
            13: 'rottenpomegranate', 14: 'rottenorange'
        }
        self.shelf_life_map = {
            'freshapple': 7,  
            'freshbanana': 5,  
            'freshguava': 6,  
            'freshpomegranate': 7,  
            'freshorange': 6,  
            'partiallyfreshapple': 4,  
            'partiallyfreshbanana': 3,  
            'partiallyfreshguava': 4,  
            'partiallyfreshpomegranate': 5,  
            'partiallyfreshorange': 4,  
            'rottenapple': 0,  
            'rottenbanana': 0,  
            'rottenguava': 0,  
            'rottenpomegranate': 0,  
            'rottenorange': 0  
        }


        self.freshness_score_map = {
            'freshapple': 1,  
            'freshbanana': 1,
            'freshguava': 1,
            'freshpomegranate': 1,
            'freshorange': 1,
            'partiallyfreshapple': 5,  
            'partiallyfreshbanana': 5,
            'partiallyfreshguava': 5,
            'partiallyfreshpomegranate': 6,
            'partiallyfreshorange': 6,
            'rottenapple': 8,  
            'rottenbanana': 8,
            'rottenguava': 9,
            'rottenpomegranate': 9,
            'rottenorange': 10
        }
        self.textract = boto3.client(
                'textract',
                aws_access_key_id=settings.ACCESS_KEY,
                aws_secret_access_key=settings.SECRET_KEY,
                region_name=settings.REGION,
             )
        self.brands = [
                "WH Protective Oil", "Colgate", "LetsShave", "Nivea", "Garnier", "Dettol",
                "Vaseline", "Himalaya", "Dabur", "Gillette", "Johnson & Johnson", "L'Oréal",
                "Parachute", "Pepsodent", "Sunsilk", "Lifebuoy", "Ponds", "Clinic Plus",
                "Head & Shoulders", "Oral-B", "Sensodyne", "Fair & Lovely", "Rexona",
                "Cinthol", "Patanjali", "Godrej", "HUL (Hindustan Unilever)", "Emami",
                "Boroplus", "Santoor", "ITC", "Park Avenue", "Fiama", "Old Spice", "Lux",
                "Wild Stone", "Axe", "Yardley", "Nirma", "Surf Excel", "Ariel", "Tide",
                "Rin", "Vim", "Medimix", "Nutralite sampriti ghee", "Pramix Food Jaggery Cube","SURYA NAMKEEN"
        ]
        self.model = load_model("backend/services/ml/finalpilotmodel.h5")

    def predict_image(self, image_path):
        print(image_path)
        img = image.load_img(image_path, target_size=(224, 224))
        img_array = image.img_to_array(img)
        img_array = np.expand_dims(img_array, axis=0)
        img_array /= 255.0

        prediction = self.model.predict(img_array)
        predicted_class_index = np.argmax(prediction, axis=1)[0]
        confidence = np.max(prediction) * 100

        predicted_label = self.class_mapping[predicted_class_index]
        predicted_label = self.class_mapping[
            predicted_class_index
        ]  # Map the predicted index to the label

        return predicted_label, confidence

    def predict_best_image(self, image_paths):
        best_label = None
        highest_confidence = 0

        # Loop through all the images
        for image_path in image_paths:
            predicted_label, confidence = self.predict_image(image_path)
            print(
                f"Image: {image_path}, Predicted Class: {predicted_label}, Confidence: {confidence:.2f}%"
            )

            # If this image has a higher confidence, update the best prediction
            if confidence > highest_confidence:
                highest_confidence = confidence
                best_label = predicted_label

        print(f"Predicted Class: {best_label}")
        print(f"Confidence: {highest_confidence:.2f}%")
        response = {
            "Predicted Class": best_label,
            "Confidence": {highest_confidence},
        }
        return response

    def load_images(self):
        self.images = [cv2.imread(image_path) for image_path in self.image_paths]
        for idx, image in enumerate(self.images):
            if image is None:
                raise FileNotFoundError(
                    f"Image not found at path: {self.image_paths[idx]}"
                )
        return self.images

    @staticmethod
    def preprocess_image_for_ocr(image):
        # Convert to grayscale
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # Denoise
        denoised = cv2.fastNlMeansDenoising(gray, None, 10, 7, 21)

        # Increase contrast using CLAHE
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        contrast = clahe.apply(denoised)

        # Threshold
        _, binary = cv2.threshold(contrast, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

        # Dilation and erosion
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        morph = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)

        return morph

    def extract_text(self, preprocessed_image):
        # Use multiple page segmentation modes and OCR engine modes
        configs = [
            "--psm 6",  # Assume a single uniform block of text
            "--psm 3",  # Fully automatic page segmentation, but no OSD
            "--psm 4",  # Assume a single column of text of variable sizes
        ]

        texts = []
        for config in configs:
            text = pytesseract.image_to_string(preprocessed_image, config=config)
            texts.append(text)

        # Choose the text with the most content
        self.text = max(texts, key=len)
        return self.text

    @staticmethod
    def extract_price(text):
        # Split text into lines
        lines = text.split("\n")

        for line in lines:
            if "MRP" in line or "M.R.P" in line:
                match = re.search(r"([\d,]+(?:\.\d{1,2})?)", line)
                if match:
                    return match.group(1).replace(",", "")  # Return the matched price
        return None  # Return None if no price found

    @staticmethod
    def extract_dates(text):
        patterns = [
            r"\b((?:JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)-\d{4})\b",
            r"\b(\d{2}/\d{2}/\d{4})\b",
            r"\b(\d{2}-\d{2}-\d{4})\b",
        ]
        dates = []
        for pattern in patterns:
            dates.extend(re.findall(pattern, text, re.IGNORECASE))
        return dates

    @staticmethod
    def compare_dates(dates):
        # Check if any dates are provided
        if not dates:
            return None, None

        date_objects = []
        for date in dates:
            # Try parsing the date with multiple formats
            for fmt in ("%b-%Y", "%b.%Y", "%d/%m/%Y", "%d-%m-%Y"):
                try:
                    date_obj = datetime.strptime(date, fmt)
                    date_objects.append(date_obj)
                    break  # Break if successfully parsed
                except ValueError:
                    continue  # Try the next format

        # If no valid dates were parsed
        if not date_objects:
            return None, None

        # Determine manufacturing and expiration dates
        mfg_date = min(date_objects).strftime("%b-%Y")
        exp_date = max(date_objects).strftime("%b-%Y")

        # Return dates based on equality
        if mfg_date == exp_date:
            return mfg_date, None
        else:
            return mfg_date, exp_date

    @staticmethod
    def find_brand_in_text(text, brand_list):
        # Loop through each brand name in the list
        for brand in brand_list:
            # Split the brand name into words
            brand_words = brand.split()
            # Check if any word from the brand is present in the text
            for word in brand_words:
                # Use regex to find the word in the text (case insensitive)
                if re.search(r"\b" + re.escape(word) + r"\b", text, re.IGNORECASE):
                    return brand  # Return the matched brand if any word is found
        return "Brand not found"

    def process_multiple_images(self):
        self.load_images()
        extracted_texts = []

        for image in self.images:
            # preprocessed_image = self.preprocess_image_for_ocr(image)
            text = self.extract_text(image)
            extracted_texts.append(text)

        # Combine the text from all images
        self.combined_text = " ".join(extracted_texts)
        return self.combined_text

    def process_images(self):
        combined_text = self.process_multiple_images()

        # print("Combined Text from All Images:")
        # print(combined_text)

        mrp = self.extract_price(combined_text)
        dates = self.extract_dates(combined_text)
        mfg_date, exp_date = self.compare_dates(dates)

        brands = self.brands

        brand = self.find_brand_in_text(combined_text, brands)

        response = {
            "name": brand,
            "expiry_date": exp_date,
            "manufacturing_date": mfg_date,
            "mrp": mrp,
            "description": (
                combined_text[:500] if len(combined_text) > 500 else combined_text
            ),
        }

        return response
    

    def extract_text(self,image_path):
        with open(image_path, 'rb') as document:
            document_bytes = document.read()

        response = self.textract.analyze_document(
            Document={'Bytes': document_bytes},
            FeatureTypes=['LAYOUT']
        )

        text_output = [block['Text'] for block in response['Blocks'] if 'Text' in block]
        return " ".join(text_output)   

    def extract_details(self,text):
        """
        Extract MRP, Manufacturing Date, and Expiration Date from text using regex with OR patterns.
        """
        mrp_pattern = r"(?:M.R.P|MRP)\s*[:\-]?\s*([\d]+(?:\.\d+)?)|MRP\s*\.\s*(\d+)/"
        mrp_match = re.search(mrp_pattern, text)
        
        if mrp_match:
            mrp = mrp_match.group(1) if mrp_match.group(1) else mrp_match.group(2)
        else:
            mrp = None

        print("Extracted MRP:", mrp)

        mfg_date_pattern = r"(?:Mfg\. Date|Mfd)\s*[:\-]?\s*([A-Z]+-\d{4})"
        mfg_date_match = re.search(mfg_date_pattern, text)
        manufacturing_date = mfg_date_match.group(1) if mfg_date_match else None
        print("Extracted Manufacturing Date:", manufacturing_date)

        exp_date_pattern = r"(?:Exp\. Date|Exp Date)\s*[:\-]?\s*([A-Z]+-\d{4})"
        exp_date_match = re.search(exp_date_pattern, text)
        expiration_date = exp_date_match.group(1) if exp_date_match else None
        print("Extracted Expiration Date:", expiration_date)

        return mrp, manufacturing_date, expiration_date

    def find_brand_in_text(self,text, brand_list):
            # Loop through each brand name in the list
            for brand in brand_list:
                # Split the brand name into words
                brand_words = brand.split()
                # Check if any word from the brand is present in the text
                for word in brand_words:
                    # Use regex to find the word in the text (case insensitive)
                    if re.search(r"\b" + re.escape(word) + r"\b", text, re.IGNORECASE):
                        return brand  # Return the matched brand if any word is found
            return "Brand not found"

    def check_expiration(self, exp_date):
        if not exp_date or exp_date == "NA":
            return None
        try:
            expiry_date = datetime.strptime(exp_date, "%Y-%m-%d")
            return datetime.now() > expiry_date
        except ValueError:
            return None

    def calculate_expected_life_span(self, exp_date):
        if not exp_date or exp_date == "NA":
            return None
        try:
            expiry_date = datetime.strptime(exp_date, "%Y-%m-%d")
            delta = expiry_date - datetime.now()
            return max(0, delta.days)
        except ValueError:
            return None
    def process_text(self):
        combined_text = " ".join([self.extract_text(image_path) for image_path in self.image_paths])

        print("Combined Text Extracted from All Images:")
        print("------------------------------------")
        print(combined_text)
        print("------------------------------------")

        mrp, mfg_date, exp_date = self.extract_details(combined_text)
        brand = self.find_brand_in_text(combined_text,self.brands)

        current_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        parsed_data = {
            "uuid": uuid.uuid4(),
            "mrp": mrp,
            "timestamp": datetime.now(),
            "brand": brand,
            "expiry_date": datetime.strptime(exp_date, "%Y-%m-%d") if exp_date else None,
            "count": self.count,
            "expired": self.check_expiration(exp_date),
            "expected_life_span": self.calculate_expected_life_span(exp_date),
        }

        product_schema = PackagedProductSchema(**parsed_data)

        print("Extracted Data as Schema:")
        print(product_schema.model_dump_json(indent=2))
        return product_schema


    def calculate_shelf_life(self,predicted_label):
        return self.shelf_life_map.get(predicted_label, None)

    # Function to calculate the freshness score based on the fruit and freshness state
    def calculate_freshness_score(self,predicted_label):
        return self.freshness_score_map.get(predicted_label, None)

    # Function to load the image and predict its class
    def predict_image(self,model, image_path):
        img = image.load_img(image_path, target_size=(224, 224))  
        img_array = image.img_to_array(img)  
        img_array = np.expand_dims(img_array, axis=0)  
        img_array /= 255.0  

        prediction = model.predict(img_array)  
        predicted_class_index = np.argmax(prediction, axis=1)[0]  
        predicted_label = self.class_mapping.get(predicted_class_index, None)
        confidence = np.max(prediction) * 100  

        return predicted_label, confidence

    # Function to predict the best image from multiple images
    def predict_best_image(self,model, image_paths):
        best_label = None
        highest_confidence = 0

        for image_path in image_paths:
            predicted_label, confidence = self.predict_image(model, image_path)
            print(f"Image: {image_path}, Predicted Class: {predicted_label}, Confidence: {confidence:.2f}%")

            if confidence > highest_confidence:
                highest_confidence = confidence
                best_label = predicted_label

        if best_label:
            shelf_life = self.calculate_shelf_life(best_label)
            freshness_score = self.calculate_freshness_score(best_label)
            print(f"\nBest Prediction: {best_label}")
            print(f"Confidence: {highest_confidence:.2f}%")
            print(f"Days Left (Shelf Life): {shelf_life} days")
            print(f"Freshness Score: {freshness_score}")
        else:
            print("No valid predictions were made.")
        response = {
            "Predicted Class": best_label,
            "Confidence": {highest_confidence},
            "Shelf Life": shelf_life,
            "Freshness Score": freshness_score,
        }
        return response
    
    def process(self,image_paths):
        return self.predict_best_image(self.model, image_paths)