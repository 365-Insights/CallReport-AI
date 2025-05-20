import base64  
import ffmpeg  
import tempfile  
import os  
import traceback  
import json
import re
from ast import literal_eval 
import requests
import mimetypes  
import asyncio
from time import sleep
from bs4 import BeautifulSoup


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
    

def fix_malformed_json(json_string):
    if not json_string or not isinstance(json_string, str):
        raise ValueError("Input must be a non-empty string")
    
    # Try parsing the JSON directly first
    try:
        return json.loads(json_string)
    except json.JSONDecodeError:
        # If direct parsing fails, try to fix common issues
        fixed_string = json_string
        
        # Step 1: Remove unescaped quotes inside string values
        # This pattern looks for string values containing unescaped quotes
        fixed_string = re.sub(r'(:\s*")([^"]*)"([^"]*")(?=[,}])', 
                              lambda m: f'{m.group(1)}{m.group(2)} {m.group(3)}',
                              fixed_string)
        
        # Step 2: Fix unclosed quotes that end with single quote (')
        fixed_string = re.sub(r':\s*"([^"]*)\'"?(?=[,}]|$)',
                             r': "\1"',
                             fixed_string)
        
        # Step 3: Handle truncated JSON structures
        # Count opening and closing braces/brackets
        open_braces = fixed_string.count('{')
        close_braces = fixed_string.count('}')
        open_brackets = fixed_string.count('[')
        close_brackets = fixed_string.count(']')
        
        # Close any unclosed structures
        fixed_string += ']' * (open_brackets - close_brackets)
        fixed_string += '}' * (open_braces - close_braces)
        
        # Try parsing the fixed string
        try:
            return json.loads(fixed_string)
        except json.JSONDecodeError:
            # If the fix didn't work, try the fallback approach
            return fallback_json_fix(json_string)


def fallback_json_fix(json_string):
    # Create a shell structure for the result
    result = {}
    
    # Look for a top-level array structure pattern
    array_match = re.search(r'^\s*{\s*"([^"]+)"\s*:\s*\[', json_string)
    if array_match:
        array_name = array_match.group(1)
        result[array_name] = []
        
        # Extract objects within the array
        object_matches = re.findall(r'{\s*"([^"]+)"\s*:', json_string)
        if object_matches and len(object_matches) > 1:
            # There's at least one nested object
            result[array_name].append({})
    
    # Extract all key-value pairs
    pairs = []
    key_value_pattern = r'"([^"]+)"\s*:\s*(?:"([^"]*)"|([^,}\]]*))(?=[,}\]]|$)'
    
    for match in re.finditer(key_value_pattern, json_string):
        key = match.group(1)
        # The value could be in different capture groups based on type
        value = match.group(2) if match.group(2) is not None else match.group(3)
        
        # Clean up the value if needed
        if value:
            value = value.strip()
            
            # Convert to appropriate type if it's not a string
            if value == 'null':
                value = None
            elif value == 'true':
                value = True
            elif value == 'false':
                value = False
            elif value and value.replace('.', '', 1).isdigit():
                # Handle numeric values (both int and float)
                value = float(value) if '.' in value else int(value)
        
        pairs.append({"key": key, "value": value})
    
    # Clean up problematic values
    for pair in pairs:
        # Remove inner quotes from string values
        if isinstance(pair["value"], str):
            # Remove any unescaped quotes in the middle of values
            pair["value"] = re.sub(r'(?<!")"(?!")', '', pair["value"])
            
            # Remove trailing single quotes
            if pair["value"].endswith("'"):
                pair["value"] = pair["value"][:-1]
    
    # Build the final object structure
    nested_object_keys = []
    for pair in pairs:
        if "Information" in pair["key"]:
            nested_object_keys.append(pair["key"])
        elif array_match and result[array_match.group(1)]:
            # If we detected an array+object structure, add to the first object in array
            if nested_object_keys:
                # Handle nested object
                nested_key = nested_object_keys[0]
                if nested_key not in result[array_match.group(1)][0]:
                    result[array_match.group(1)][0][nested_key] = {}
                result[array_match.group(1)][0][nested_key][pair["key"]] = pair["value"]
            else:
                # Add directly to the first object in array
                result[array_match.group(1)][0][pair["key"]] = pair["value"]
        else:
            # Add to root object
            result[pair["key"]] = pair["value"]
    
    # Last attempt to fix if nothing was added to the result
    if not result:
        result = extract_key_values_aggressively(json_string)
        
    if not result:
        raise ValueError("Failed to fix the malformed JSON")
    
    return result


def extract_key_values_aggressively(json_string):
    # Create a simple dict to store extracted values
    extracted = {}
    
    # Look for any pattern that resembles a key-value pair
    key_value_pattern = r'"([^"]+)"\s*:\s*(?:"([^"]*)"?|([^,}\]]*))(?=,|}|\]|$)'
    
    for match in re.finditer(key_value_pattern, json_string):
        key = match.group(1)
        # Value could be in different capture groups
        raw_value = match.group(2) if match.group(2) is not None else match.group(3)
        
        if raw_value:
            # Clean the value: remove unescaped quotes and trailing single quotes
            value = raw_value.strip().replace('"', '')
            if value.endswith("'"):
                value = value[:-1]
                
            # Try to convert to appropriate data type
            if value == 'null':
                extracted[key] = None
            elif value == 'true':
                extracted[key] = True
            elif value == 'false':
                extracted[key] = False
            elif value and value.replace('.', '', 1).isdigit():
                # Convert to number if possible
                extracted[key] = float(value) if '.' in value else int(value)
            else:
                extracted[key] = value
    
    return extracted


def load_preprocess_json(text: str):  
    # print("Begginging", text)
    # Step 1: Remove outer quotes if present  
    if text.startswith('"') and text.endswith('"'):  
        text = text[1:-1]  
    # text = text.replace("false", "0").replace("true", "1")
    # Step 2: Normalize escaped characters (e.g., \\\" -> \")  
    text = text.replace("\\\\\\", "\\")
    text = text.replace('\\"', '"').replace('\\\\', '\\')  
    # text = str(text).strip("'<>()\\ \"").replace('\'', '\"')
    text = re.sub(r'(?<=["])\'(?=[^"]*["])', '"', text)
    # print("END", text)
    # Step 3: Attempt to parse the cleaned JSON string  
    try: 
        parsed = fix_malformed_json(text)
        # parsed = json.loads(text)   
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


def get_imprint_url(base_url):  
    # Try to find common imprint page URLs  
    common_imprint_paths = [ 'pages/imprint', 'imprint', 'impressum', 'about', 'legal']  
    for path in common_imprint_paths:  
        url = f"{base_url.rstrip('/')}/{path}"  
        response = requests.get(url)  
        if response.status_code == 200:  
            return url  
        sleep(0.2)
    return None


def parse_imprint(url):  
    response = requests.get(url)  
    soup = BeautifulSoup(response.content, 'html.parser')  
    text = soup.get_text(separator='\n')  
    return text  

def preprocess_text(text):  
    # Remove leading and trailing whitespace  
    text = text.strip()  
      
    # Replace multiple newlines and spaces with a single space  
    text = ' '.join(text.split())  
      
    # Optionally, you can also remove extra spaces between sentences  
    text = text.replace(' .', '.')  
      
    return text

def get_company_imprint(base_url):  
    try:
        imprint_url = get_imprint_url(base_url)  
        if imprint_url:  
            imprint_text = parse_imprint(imprint_url)  
            print(f"Imprint from {imprint_url}")  
            return preprocess_text(imprint_text)
        else:  
            return 
    except Exception:
        print("Got an error during imprint: ", traceback.format_exc())
        return

def merge_dicts_recursive(dict1: dict, dict2: dict) -> dict:  
    """Merge dicts with priority values on dict1"""
    merged = {}  
  
    # Get all unique keys from both dictionaries  
    all_keys = set(dict1.keys()).union(dict2.keys())  
  
    for key in all_keys:  
        value1 = dict1.get(key)  
        value2 = dict2.get(key)  
  
        if isinstance(value1, dict) and isinstance(value2, dict):  
            # If both values are dictionaries, merge them recursively  
            merged[key] = merge_dicts_recursive(value1, value2)  
        elif value1 is not None:  
            # If the key exists in dict1, use its value  
            merged[key] = value1  
        else:  
            # Otherwise, use the value from dict2  
            merged[key] = value2  
  
    return merged

with open("utils/lang_voice.json", "r") as f:
    lang2voice = json.loads(f.read())


with open("utils/locale_lang.json", "r") as f:
    locale2lang = json.loads(f.read())
from time import time  
from functools import wraps  
import asyncio  
  
def timing(print_args=False):  # Add a parameter to control argument printing  
    def decorator(f):  
        @wraps(f)  
        def sync_wrap(*args, **kw):  
            ts = time()  
            result = f(*args, **kw)  
            te = time()  
  
            if print_args:  
                # Shorten arguments for printing if they exceed 50 characters  
                args_str = ', '.join([str(arg)[:50] + ('...' if len(str(arg)) > 50 else '') for arg in args])  
                kw_str = ', '.join([f"{k}={str(v)[:50]}{'...' if len(str(v)) > 50 else ''}" for k, v in kw.items()])  
                print('func:%r args:[%r, %r] took: %2.4f sec' %   
                      (f.__name__, args_str, kw_str, te-ts))  
            else:  
                print('func:%r took: %2.4f sec' % (f.__name__, te-ts))  
  
            return result  
  
        @wraps(f)  
        async def async_wrap(*args, **kw):  
            ts = time()  
            result = await f(*args, **kw)  
            te = time()  
  
            if print_args:  
                # Shorten arguments for printing if they exceed 50 characters  
                args_str = ', '.join([str(arg)[:50] + ('...' if len(str(arg)) > 50 else '') for arg in args])  
                kw_str = ', '.join([f"{k}={str(v)[:50]}{'...' if len(str(v)) > 50 else ''}" for k, v in kw.items()])  
                print('func:%r args:[%r, %r] took: %2.4f sec' %   
                      (f.__name__, args_str, kw_str, te-ts))  
            else:  
                print('func:%r took: %2.4f sec' % (f.__name__, te-ts))  
  
            return result  
  
        # Check if the function is asynchronous  
        if asyncio.iscoroutinefunction(f):  
            return async_wrap  
        else:  
            return sync_wrap  
    return decorator    
