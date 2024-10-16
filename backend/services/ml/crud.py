from backend.services.commons.base import BaseService
import pytesseract
import cv2
import numpy as np
import re
from datetime import datetime
from keras.api.preprocessing import image
from keras.api.models import load_model



class ImageProcessor(BaseService):
    __item_name__ = "ML_OCR"

    def __init__(self, tesseract_cmd, image_path):
        pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
        self.image_paths = image_path
        self.image_path = image_path[0]
        self.text = None
        self.model = load_model("backend/services/ml/freshnessmodel.h5")
        self.class_mapping =  {
            0: "freshapples",
            1: "freshbanana",
            2: "freshbittergroud",
            3: "freshbottlegourd",
            4: "freshbroccoli",
            5: "freshcabbages",
            6: "freshcapsicum",
            7: "freshcarrots",
            8: "freshcauliflower",
            9: "freshchilli",
            10: "freshcorn",
            11: "freshcucumber",
            12: "fresheggplant",
            13: "freshgarlic",
            14: "freshgrapes",
            15: "freshguava",
            16: "freshkiwi",
            17: "freshlemons",
            18: "freshmangoes",
            19: "freshokra",
            20: "freshonions",
            21: "freshoranges",
            22: "freshpapaya",
            23: "freshpineapple",
            24: "freshpomegranate",
            25: "freshpotato",
            26: "freshpumpkin",
            27: "freshradish",
            28: "freshspinach",
            29: "freshstrawberries",
            30: "freshtomato",
            31: "freshwatermelon",
            32: "rottenapples",
            33: "rottenbanana",
            34: "rottenbittergroud",
            35: "rottenbottlegourd",
            36: "rottenbroccoli",
            37: "rottencabbages",
            38: "rottencapsicum",
            39: "rottencarrots",
            40: "rottencauliflower",
            41: "rottenchilli",
            42: "rottencorn",
            43: "rottencucumber",
            44: "rotteneggplant",
            45: "rottengarlic",
            46: "rottengrapes",
            47: "rottenguava",
            48: "rottenkiwi",
            49: "rottenlemons",
            50: "rottenmangoes",
            51: "rottenokra",
            52: "rottenonions",
            53: "rottenoranges",
            54: "rottenpapaya",
            55: "rottenpineapple",
            56: "rottenpomegranate",
            57: "rottenpotato",
            58: "rottenpumpkin",
            59: "rottenradish",
            60: "rottenspinach",
            61: "rottenstrawberries",
            62: "rottentomato",
            63: "rottenwatermelon",
        }
    
    def predict_image(self):
        img = image.load_img(
            self.image_path, target_size=(224, 224)
        )
        img_array = image.img_to_array(img) 
        img_array = np.expand_dims(img_array, axis=0)
        img_array /= 255.0

        prediction = self.model.predict(img_array)
        predicted_class_index = np.argmax(prediction, axis=1)[
            0
        ] 
        confidence = np.max(prediction) * 100

        predicted_label = self.class_mapping[
            predicted_class_index
        ] 
        print(f"Predicted Class: {predicted_label}")
        print(f"Confidence: {confidence:.2f}%")
        response = {
            "Predicted Class": predicted_label,
            "Confidence": {confidence},
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
        if not dates:
            return None, None
        date_objects = []
        for date in dates:
            try:
                date_obj = datetime.strptime(date, "%b-%Y")
            except ValueError:
                try:
                    date_obj = datetime.strptime(date, "%d/%m/%Y")
                except ValueError:
                    try:
                        date_obj = datetime.strptime(date, "%d-%m-%Y")
                    except ValueError:
                        continue
            date_objects.append(date_obj)
        if not date_objects:
            return None, None
        return (
            min(date_objects).strftime("%b-%Y"),
            max(date_objects).strftime("%b-%Y"),
        )

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

        brands = [
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
            "Rin",
            "Vim",
            "Medimix",
            "WH Protective Oil",
        ]

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