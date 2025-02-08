import google.generativeai as genai
from dotenv import load_dotenv
from pathlib import Path
import os
from fastapi import HTTPException

load_dotenv()

# Set up the Gemini API key and model configuration
gene_ai_key = os.getenv('GENAI_API_KEY')
genai.configure(api_key=gene_ai_key)

MODEL_CONFIG = {
  "temperature": 0.2,
  "top_p": 1,
  "top_k": 32,
  "max_output_tokens": 4096,
}

safety_settings = [
  {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
  {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
  {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
  {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"}
]

model = genai.GenerativeModel(model_name="gemini-1.5-flash", generation_config=MODEL_CONFIG, safety_settings=safety_settings)

def image_format(image_path):
    img = Path(image_path)

    if not img.exists():
        raise FileNotFoundError(f"Could not find image: {img}")

    image_parts = [
        {"mime_type": "image/jpeg", "data": img.read_bytes()}  # Assuming JPEG format for uploaded image
    ]
    return image_parts

def gemini_output(image_path, system_prompt, user_prompt):
    try:
        image_info = image_format(image_path)
        input_prompt = [system_prompt, image_info[0], user_prompt]
        response = model.generate_content(input_prompt)
        return response.text
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error extracting data from invoice: {str(e)}")

# Define system and user prompts

