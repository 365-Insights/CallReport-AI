import ffmpeg  
import tempfile  
import base64  
import os  
import traceback  
import uuid
def convert_base64_webm_to_wav(base64_audio_data, output_filename):  
    """  
    Converts a base64-encoded .webm audio file to a .wav file.  
      
    Parameters:  
        base64_audio_data (str): The base64-encoded .webm audio data.  
        output_filename (str): The desired name of the output .wav file.  
  
    Returns:  
        str: The path to the converted .wav file, or None if an error occurred.  
    """  
    try:  
        # Decode the base64 audio data  
        audio_data = base64.b64decode(base64_audio_data)  
          
        # Create a temporary file for the .webm data  
        with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as temp_webm_file:  
            temp_webm_file.write(audio_data)  
            temp_webm_path = temp_webm_file.name  
        print(f"Temporary .webm file created at: {temp_webm_path}")  
          
        # Create a temporary directory for the output .wav file  
        output_path = output_filename
        print(f"Output .wav file will be saved at: {output_path}")  
        print("DOES file exists: ", os.path.exists(temp_webm_path))
        # Convert the .webm file to .wav using ffmpeg-python  
        ffmpeg.input(temp_webm_path).output(output_path).run()  
        print("Conversion completed successfully.")  
          
        # Clean up the temporary .webm file  
        os.remove(temp_webm_path)  
        print(f"Temporary .webm file deleted: {temp_webm_path}")  
          
        return output_path  
    except ffmpeg.Error as e:  
        print(f"Error during ffmpeg conversion: {e}")  
        print(traceback.format_exc())  
        return None  
    except Exception as e:  
        print(f"An unexpected error occurred: {e}")  
        print(traceback.format_exc())  
        return None  