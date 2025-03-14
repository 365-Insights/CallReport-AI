import base64  
import ffmpeg  
import tempfile  
import os  
import traceback  
import json
import re
from ast import literal_eval 
import mimetypes  
  
def sanitize_base64_string(base64_audio_data):  
    """  
    Sanitizes the Base64 string by removing prefixes and fixing padding.  
    """  
    try:  
        # Remove any data URI scheme prefix (e.g., "data:audio/webm;base64,")  
        if "," in base64_audio_data:  
            base64_audio_data = base64_audio_data.split(",")[1]  
  
        # Fix padding by ensuring the length is a multiple of 4  
        missing_padding = len(base64_audio_data) % 4  
        if missing_padding != 0:  
            base64_audio_data += "=" * (4 - missing_padding)  
  
        return base64_audio_data  
    except Exception as e:  
        print(f"Error sanitizing Base64 string: {e}")  
        print(traceback.format_exc())  
        return None  
  
  
def detect_audio_format(base64_audio_data):  
    """  
    Detects the format of the audio based on the Base64 data URI prefix.  
    """  
    try:  
        # Extract MIME type from the Base64 string  
        if "," in base64_audio_data and base64_audio_data.startswith("data:"):  
            mime_type = base64_audio_data.split(";")[0].split(":")[1]  
            extension = mimetypes.guess_extension(mime_type)  
            if extension:  
                return mime_type, extension  
        # Default to application/octet-stream  
        return "application/octet-stream", ".bin"  
    except Exception as e:  
        print(f"Error detecting audio format: {e}")  
        print(traceback.format_exc())  
        return None, None  
  
  
def convert_base64_audio_to_wav(base64_audio_data, output_filename):  
    """  
    Converts a Base64-encoded audio file (webm, aac, etc.) to a .wav file.  
    """  
    try:  
        # Sanitize the Base64 string  
        sanitized_base64 = sanitize_base64_string(base64_audio_data)  
        if sanitized_base64 is None:  
            raise ValueError("Failed to sanitize Base64 string")  
  
        # Detect the audio format  
        mime_type, extension = detect_audio_format(base64_audio_data)  
        if not mime_type or not extension:  
            raise ValueError("Unable to detect audio format")  
  
        print(f"Detected MIME type: {mime_type}, File extension: {extension}")  
  
        # Decode the Base64 audio data  
        audio_data = base64.b64decode(sanitized_base64)  
  
        # Create a temporary file for the audio data  
        with tempfile.NamedTemporaryFile(delete=False, suffix=extension) as temp_audio_file:  
            temp_audio_file.write(audio_data)  
            temp_audio_path = temp_audio_file.name  
        print(f"Temporary audio file created at: {temp_audio_path}")  
  
        # Define output path for .wav file  
        output_path = output_filename  
        print(f"Output .wav file will be saved at: {output_path}")  
  
        # Convert the audio file to .wav using ffmpeg-python  
        ffmpeg.input(temp_audio_path).output(output_path).run()  
        print("Conversion completed successfully.")  
  
        # Clean up the temporary audio file  
        os.remove(temp_audio_path)  
        print(f"Temporary audio file deleted: {temp_audio_path}")  
  
        return output_path  
    except ffmpeg.Error as e:  
        print(f"Error during ffmpeg conversion: {e}")  
        print(traceback.format_exc())  
        return None  
    except Exception as e:  
        print(f"An unexpected error occurred: {e}")  
        print(traceback.format_exc())  
        return None  

def load_preprocess_json(text: str):  
    # print("Begginging", text)
    # Step 1: Remove outer quotes if present  
    if text.startswith('"') and text.endswith('"'):  
        text = text[1:-1]  
  
    # Step 2: Normalize escaped characters (e.g., \\\" -> \")  
    text = text.replace('\\"', '"').replace('\\\\', '\\')  
    # text = str(text).strip("'<>()\\ \"").replace('\'', '\"')
    text = text.replace("\'", "\"")
    # print("END", text)
    # Step 3: Attempt to parse the cleaned JSON string  
    try:  
        parsed = json.loads(text)  

        # Step 4: If the result is still a string (e.g., nested JSON), parse it again  
        if isinstance(parsed, str):  
            try:  
                return json.loads(parsed)  
            except json.JSONDecodeError:  
                pass  # It's just a string, not nested JSON  
  
        return parsed  
    except json.JSONDecodeError as e:  
        # Raise a descriptive error if parsing fails  
        print(traceback.format_exc())
        raise ValueError(f"Failed to parse JSON: {text}") from e  


with open("utils/lang_voice.json", "r") as f:
    lang2voice = json.loads(f.read())