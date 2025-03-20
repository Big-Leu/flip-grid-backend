import numpy as np
from tensorflow.keras.preprocessing import image
from tensorflow.keras.models import load_model

# Load the saved model
model = load_model("E:/FlipkartGrid/models/finalpilotmodel.h5")

# Your saved class mapping dictionary
class_mapping = {
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

# Define a dictionary for the shelf life (days left) for each fruit and freshness state
shelf_life_map = {
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

# Freshness scores for different fruit states (1-10 scale)
freshness_score_map = {
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


# Function to calculate the shelf life (days left) based on the fruit and freshness state
def calculate_shelf_life(predicted_label):
    return shelf_life_map.get(predicted_label, None)


# Function to calculate the freshness score based on the fruit and freshness state
def calculate_freshness_score(predicted_label):
    return freshness_score_map.get(predicted_label, None)


# Function to load the image and predict its class
def predict_image(model, image_path):
    img = image.load_img(image_path, target_size=(224, 224))
    img_array = image.img_to_array(img)
    img_array = np.expand_dims(img_array, axis=0)
    img_array /= 255.0

    prediction = model.predict(img_array)
    predicted_class_index = np.argmax(prediction, axis=1)[0]
    predicted_label = class_mapping.get(predicted_class_index, None)
    confidence = np.max(prediction) * 100

    return predicted_label, confidence


# Function to predict the best image from multiple images
def predict_best_image(model, image_paths):
    best_label = None
    highest_confidence = 0

    for image_path in image_paths:
        predicted_label, confidence = predict_image(model, image_path)
        print(
            f"Image: {image_path}, Predicted Class: {predicted_label}, Confidence: {confidence:.2f}%"
        )

        if confidence > highest_confidence:
            highest_confidence = confidence
            best_label = predicted_label

    if best_label:
        shelf_life = calculate_shelf_life(best_label)
        freshness_score = calculate_freshness_score(best_label)
        print(f"\nBest Prediction: {best_label}")
        print(f"Confidence: {highest_confidence:.2f}%")
        print(f"Days Left (Shelf Life): {shelf_life} days")
        print(f"Freshness Score: {freshness_score}")
    else:
        print("No valid predictions were made.")

    return best_label, highest_confidence


# Example usage with multiple image paths
image_paths = ["C:/Users/Arun/Desktop/5.jpg", "C:/Users/Arun/Desktop/6.jpg"]

predict_best_image(model, image_paths)
