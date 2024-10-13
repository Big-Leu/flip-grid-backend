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
        self.image_path = image_path
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

    def preprocess_image(self):
        # Read the image
        img = cv2.imread(self.image_path)

        # Convert to grayscale
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # Apply Gaussian Blur to remove noise
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)

        # Apply adaptive thresholding to get binary image (to enhance text visibility)
        thresh = cv2.adaptiveThreshold(
            blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 11, 2
        )

        # Use morphological operations to remove small noise
        kernel = np.ones((3, 3), np.uint8)
        processed_img = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)

        return processed_img

    def extract_text(self):
        self.text = pytesseract.image_to_string(self.image_path)
        return self.text

    @staticmethod
    def extract_price_simple(text):
        # Split text into lines
        lines = text.split("\n")

        for line in lines:
            if "MRP" in line or "M.R.P" in line:
                # Now extract the price using a simple regex
                match = re.search(r"([\d,]+(?:\.\d{1,2})?)", line)
                if match:
                    return match.group(1).replace(",", "")  # Return the matched price
        return None  # Return None if no price found

    @staticmethod
    def extract_date(text):
        # Regex pattern to find dates in the format "MAR-2027"
        pattern = r"\b([A-Z]{3}-\d{4})\b"  # Match three uppercase letters followed by a dash and four digits
        matches = re.findall(pattern, text)
        return matches

    @staticmethod
    def compare_dates(dates):
        # Convert date strings to datetime objects for comparison
        date_objects = [datetime.strptime(date, "%b-%Y") for date in dates]

        if len(date_objects) != 2:
            return None, None

        # Compare dates
        mfg_date = min(date_objects).strftime("%b-%Y")
        exp_date = max(date_objects).strftime("%b-%Y")

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
        return "Brand not found"  # Return this if no brand is found

    def process_image(self):
        # Preprocess image
        self.preprocess_image()

        # Extract text from the image
        text = self.extract_text()

        # Extract price (MRP) from the text
        mrp = self.extract_price_simple(text)

        # Extract dates from the text
        dates = self.extract_date(text)
        mfg_date, exp_date = self.compare_dates(dates)

        # List of brand names
        brands = [
            "WH Protective Oil", "Colgate", "LetsShave", "Nivea", "Garnier", "Dettol", "Vaseline",
            "Himalaya", "Dabur", "Gillette", "Johnson & Johnson", "L'Oréal", "Parachute", "Pepsodent",
            "Sunsilk", "Lifebuoy", "Ponds", "Clinic Plus", "Head & Shoulders", "Oral-B", "Sensodyne",
            "Fair & Lovely", "Rexona", "Cinthol", "Patanjali", "Godrej", "HUL (Hindustan Unilever)",
            "Emami", "Boroplus", "Santoor", "ITC", "Park Avenue", "Fiama", "Old Spice", "Lux", "Wild Stone",
            "Axe", "Yardley", "Nirma", "Surf Excel", "Ariel", "Tide", "Rin", "Vim", "Medimix", "WH Protective Oil"
        ]

        # Find the brand in the text
        brand = self.find_brand_in_text(text, brands)

        # Construct the response
        response = {
            "name": brand,
            "expiry_date": exp_date,
            "mrp": mrp,
            "description": "something"
        }

        return response