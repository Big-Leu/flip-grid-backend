import base64


def base64_encode_string(original_string: str) -> str:
    # Convert string to bytes
    byte_data = original_string.encode("utf-8")
    base64_encoded = base64.b64encode(byte_data)
    base64_string = base64_encoded.decode("utf-8")

    return base64_string


def base64_encode(data: str) -> str:
    return base64.b64encode(data.encode("utf-8")).decode("utf-8")


def base64_decode(data: str) -> str:
    return base64.b64decode(data).decode("utf-8")


def base64_decode_string(encoded_string: str) -> str:
    byte_data = base64.b64decode(encoded_string)
    original_string = byte_data.decode("utf-8")
    return original_string
