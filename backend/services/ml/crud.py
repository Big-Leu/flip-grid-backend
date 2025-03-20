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

    def __init__(self, tesseract_cmd, image_path, count):
        pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
        self.image_paths = image_path
        self.count = count
        self.text = None

        self.class_mapping = {
            0: "freshapple",
            1: "freshbanana",
            2: "freshguava",
            3: "freshpomegranate",
            4: "freshorange",
            5: "partiallyfreshapple",
            6: "partiallyfreshbanana",
            7: "partiallyfreshguava",
            8: "partiallyfreshpomegranate",
            9: "partiallyfreshorange",
            10: "rottenapple",
            11: "rottenbanana",
            12: "rottenguava",
            13: "rottenpomegranate",
            14: "rottenorange",
        }
        self.shelf_life_map = {
            "freshapple": 7,
            "freshbanana": 5,
            "freshguava": 6,
            "freshpomegranate": 7,
            "freshorange": 6,
            "partiallyfreshapple": 4,
            "partiallyfreshbanana": 3,
            "partiallyfreshguava": 4,
            "partiallyfreshpomegranate": 5,
            "partiallyfreshorange": 4,
            "rottenapple": 0,
            "rottenbanana": 0,
            "rottenguava": 0,
            "rottenpomegranate": 0,
            "rottenorange": 0,
        }

        self.freshness_score_map = {
            "freshapple": 1,
            "freshbanana": 1,
            "freshguava": 1,
            "freshpomegranate": 1,
            "freshorange": 1,
            "partiallyfreshapple": 5,
            "partiallyfreshbanana": 5,
            "partiallyfreshguava": 5,
            "partiallyfreshpomegranate": 6,
            "partiallyfreshorange": 6,
            "rottenapple": 8,
            "rottenbanana": 8,
            "rottenguava": 9,
            "rottenpomegranate": 9,
            "rottenorange": 10,
        }
        self.textract = boto3.client(
            "textract",
            aws_access_key_id=settings.ACCESS_KEY,
            aws_secret_access_key=settings.SECRET_KEY,
            region_name=settings.REGION,
        )
        self.brands = [
            "WH Protective Oil",
            "Colgate",
            "LetsShave",
            "Nivea",
            "Garnier",
            "Dettol",
            "Vaseline",
            "Himalaya",
            "Dabur",
            "Gillette",
            "Johnson & Johnson",
            "L'Oréal",
            "Parachute",
            "Pepsodent",
            "Sunsilk",
            "Lifebuoy",
            "Ponds",
            "Clinic Plus",
            "Head & Shoulders",
            "Oral-B",
            "Sensodyne",
            "Fair & Lovely",
            "Rexona",
            "Cinthol",
            "Patanjali",
            "Godrej",
            "HUL (Hindustan Unilever)",
            "Emami",
            "Boroplus",
            "Santoor",
            "ITC",
            "Park Avenue",
            "Fiama",
            "Old Spice",
            "Lux",
            "Wild Stone",
            "Axe",
            "Yardley",
            "Nirma",
            "Surf Excel",
            "Ariel",
            "Tide",
            "Vim",
            "Medimix",
            "Nutralite sampriti ghee",
            "Pramix Food Jaggery Cube",
            "SURYA NAMKEEN",
            "Goodknight",
            "Shudh Ghee"
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

    def extract_text(self, image_path):
        with open(image_path, "rb") as document:
            document_bytes = document.read()

        response = self.textract.analyze_document(
            Document={"Bytes": document_bytes}, FeatureTypes=["LAYOUT"]
        )

        text_output = [block["Text"] for block in response["Blocks"] if "Text" in block]
        return " ".join(text_output)

    def extract_details(self, text):
        """
        Extract MRP, Manufacturing Date, and Expiration Date from the text using regex.
        """
        # Extract MRP
        mrp_match = re.search(
            r"(?:Rs|MRP|₹)[\s.:₹]*([\d]+(?:\.\d+)?)(?:[/-])?", text, re.IGNORECASE
        )
        mrp = mrp_match.group(1) if mrp_match else None

        # Extract all dates from the text
        # unique_dates = sorted(set(re.findall(r"(\d{2}\.\d{2}\.\d{2})", text) + re.findall(r"(\b\d{2}/\d{4}\b)", text)))
        unique_dates = sorted(
            set(
                re.findall(r"(\d{2}\.\d{2}\.\d{2})", text)  # dd.mm.yy format
                + re.findall(r"(\b\d{2}/\d{2}\b)", text)  # mm/yy format
                + re.findall(r"(\b\d{2}/\d{4}\b)", text)  # mm/yyyy format
            )
        )
        if len(unique_dates) > 2:
            unique_dates = unique_dates[:2]  # Keep only the first two dates

        print(
            "Unique Dates Found (raw):", unique_dates
        )  # First print for raw extracted dates

        updated_dates = []
        # for date_str in unique_dates:
        #     if len(date_str) == 7 and '/' in date_str:  # mm/yyyy format
        #         # Convert mm/yyyy to 00.mm.yyyy
        #         month, year = date_str.split('/')
        #         date_str = f"01.{month}.{year}"
        #     elif len(date_str.split('/')) == 3:  # dd/mm/yyyy format
        #         # Convert dd/mm/yyyy to dd.mm.yyyy
        #         date_str = date_str.replace('/', '.')
        #     # Add the date directly without parsing
        #     updated_dates.append(date_str)
        for date_str in unique_dates:
            if len(date_str) == 7 and "/" in date_str:  # mm/yyyy format
                month, year = date_str.split("/")
                date_str = f"01.{month}.{year[-2:]}"  # Convert to dd.mm.yy
            elif len(date_str) == 5 and "/" in date_str:  # mm/yy format
                month, year = date_str.split("/")
                date_str = f"01.{month}.{year}"  # Convert to dd.mm.yy
            elif len(date_str.split("/")) == 3:  # dd/mm/yyyy format
                day, month, year = date_str.split("/")
                date_str = f"{day}.{month}.{year[-2:]}"  # Convert to dd.mm.yy
            updated_dates.append(date_str)

        print("Processed Updated Dates:", updated_dates)

        manufacturing_dates = []
        expiration_dates = []

        if len(unique_dates) == 2:
            # Compare the two dates
            date1, date2 = self.compare_dates(updated_dates[0], updated_dates[1])
            manufacturing_dates.append(date1)
            expiration_dates.append(date2)
        elif len(unique_dates) == 1:
            # If there's only one date, consider it as the manufacturing and expiration date
            manufacturing_dates.append(updated_dates[0])
            expiration_dates.append(None)
        else:
            # For any unexpected number of dates, fallback
            manufacturing_dates.append(None)
            expiration_dates.append(None)

        return mrp, manufacturing_dates, expiration_dates

    def extract_brand(self, text):
        """
        Extract brand from the given text based on key terms.
        """
        key_terms = ["MRP", "Mfd", "Exp.", "Manufactured", "Marketed By"]
        brand_count = {}
        closest_brand = None
        min_distance = float("inf")  # Initialize with a large number

        for brand in self.brands:
            matches = list(re.finditer(re.escape(brand), text, re.IGNORECASE))
            if matches:
                brand_count[brand] = len(matches)
                for match in matches:
                    brand_position = match.start()
                    for term in key_terms:
                        term_match = re.search(term, text, re.IGNORECASE)
                        if term_match:
                            term_position = term_match.start()
                            distance = abs(brand_position - term_position)
                            if distance < min_distance:
                                min_distance = distance
                                closest_brand = brand

        if brand_count:
            most_frequent_brand = max(brand_count, key=brand_count.get)
            return (
                most_frequent_brand
                if brand_count[most_frequent_brand] > 1
                else closest_brand
            )

        return "BRAND NOT FOUND"

    def compare_dates(self, date1, date2):
        """
        Compare two dates and return the earlier or later date.

        Args:
        - date1: First date string in the format 'dd.mm.yy'
        - date2: Second date string in the format 'dd.mm.yy'

        Returns:
        - A tuple of (earlier_date, later_date)
        """
        d1 = datetime.strptime(date1, "%d.%m.%y")
        d2 = datetime.strptime(date2, "%d.%m.%y")

        if d1 < d2:
            return (date1, date2)
        else:
            return (date2, date1)

    def check_expiration(self,expiration_date_list):
        if expiration_date_list:
            # Filter out any None values and check expiration
            expiration_dates = [datetime.strptime(date, "%d.%m.%y") for date in expiration_date_list if date]
            return any(date < datetime.now() for date in expiration_dates)
        return False

    def calculate_expected_life_span(self,expiration_date_list):
        if expiration_date_list:
            # Filter out any None values and parse dates
            expiration_dates = [datetime.strptime(date, "%d.%m.%y") for date in expiration_date_list if date]
            # Calculate remaining days for future dates only
            remaining_days = [(date - datetime.now()).days for date in expiration_dates if date > datetime.now()]
            return min(remaining_days) if remaining_days else 0  # Return the smallest positive remaining days
        return 0

    def process_text(self):
        combined_text = " ".join(
            [self.extract_text(image_path) for image_path in self.image_paths]
        )

        print("Combined Text Extracted from All Images:")
        print("------------------------------------")
        print(combined_text)
        print("------------------------------------")

        mrp, mfg_date, exp_date = self.extract_details(combined_text)
        print("extracted details", mrp, mfg_date, exp_date)
        
        brand = self.extract_brand(combined_text)
        
        # Safely extract expiry_date
        expiry_date = None
        if exp_date and len(exp_date) > 0:
            try:
                expiry_date = datetime.strptime(str(exp_date[0]), "%d.%m.%y")
            except ValueError as e:
                print("Error parsing expiry date:", e)
        print("Extracted Brand:", brand)
        print("Extracted MRP:", mrp)
        print("Extracted Manufacturing Date:", mfg_date)
        print("Extracted Expiry Date:", expiry_date)
        print("check_product_expiration:", self.check_expiration(exp_date))
        print("calculate_expected_life_span:", self.calculate_expected_life_span(exp_date))
        expiry_date_str = str(exp_date[0]) if exp_date and len(exp_date) > 0 and exp_date[0] not in [None, "None"] else "nope"
        parsed_data = {
            "uuid": uuid.uuid4(),
            "mrp": mrp,
            "timestamp": datetime.now(),
            "brand": brand,
            "expiry_date": expiry_date_str,
            "count": self.count,
            "expired": self.check_expiration(exp_date),
            "expected_life_span": self.calculate_expected_life_span(exp_date),
        }
        print(parsed_data)
        product_schema = PackagedProductSchema(**parsed_data)

        print("Extracted Data as Schema:")
        print(product_schema.model_dump_json(indent=2))
        return product_schema
    
    def calculate_shelf_life(self, predicted_label):
        return self.shelf_life_map.get(predicted_label, None)

    # Function to calculate the freshness score based on the fruit and freshness state
    def calculate_freshness_score(self, predicted_label):
        return self.freshness_score_map.get(predicted_label, None)

    # Function to load the image and predict its class
    def predict_image(self, model, image_path):
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
    def predict_best_image(self, model, image_paths):
        best_label = None
        highest_confidence = 0

        for image_path in image_paths:
            predicted_label, confidence = self.predict_image(model, image_path)
            print(
                f"Image: {image_path}, Predicted Class: {predicted_label}, Confidence: {confidence:.2f}%"
            )

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

    def process(self, image_paths):
        return self.predict_best_image(self.model, image_paths)
