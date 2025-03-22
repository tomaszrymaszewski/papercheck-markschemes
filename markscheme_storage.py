import os
import re
import base64
import json
from io import BytesIO
from PIL import Image
import google.generativeai as genai

# ✅ Configure Gemini API (Replace with your API key)
genai.configure(api_key="AIzaSyCKl7FvCPoNBklNf1klaImZIbcGFXuTlYY")

# ✅ Improved Gemini API Configurations with Enhanced Prompt
CONFIGS = {
    "prompt": """
    Analyze this exam mark scheme image with high precision. Extract all marking criteria, point allocations, and expected answers.

    Return a JSON object conforming to this schema:
    {
      "question_number": [  // e.g., "1a", "2", "3b", "6i", "6ii", "4a", "10b", "9aii", "8ci" etc.
        {
          "point_id": number,  // Sequential ID starting from 1
          "marks": number,  // How many marks this point is worth (typically 1)
          "criteria": "string",  // The description of what earns this mark
          "expected_answer": "string",  // The specific answer or working expected
          "mark_type": "string"  // Specific mark type as described below
        }
      ]
    }

    DETAILED INSTRUCTIONS:
    1. Question Structure:
       - Use the exact question number/identifier as the top-level key
       - If a question has parts (a, b, c) or sub-parts (i, ii, iii), nest them appropriately
       - Always preserve the original numbering/lettering system

    2. Mark Types - PRECISELY identify and categorize each mark as one of the following:
       - "M" or "Method": Awarded for using a correct method, even if the final answer is wrong
       - "A" or "Accuracy": Given for correct final answers or correct intermediate steps after a method
       - "B" or "Independent": Awarded for standalone correct answers that don't require a previous method step
       - "E" or "Explanation": Given for correct reasoning, justification, or written explanations
       - "D" or "Dependent": Given only if a previous method mark is awarded
       - "FT" or "Follow Through": Allows credit for correct working based on an earlier mistake
       - "QWC": Quality of written communication marks
       - "AO1", "AO2", "AO3", etc.: Assessment objective marks
       - If marks are numbered (e.g., M1, M2, A1), include the full identifier

    3. Format Guidelines:
       - For mathematical expressions, preserve the exact notation
       - For multiple acceptable answers, include all alternatives separated by " OR "
       - For ranges of acceptable answers, use format "between X and Y" or "X to Y"
       - If a marking point is worth multiple marks, accurately reflect this in the "marks" field
       - Pay special attention to dependencies between marks (e.g., "A1 dependent on M1")

    4. Special Handling:
       - If alternative methods are provided, include all valid approaches
       - If the mark scheme uses annotations (tick marks, ✓, etc.), interpret what each represents
       - Identify and flag "consequential" or "follow-through" marking where students can get credit despite earlier errors
       - For "seen" or "award" marks (e.g., "award 1 mark for..."), clearly identify the criteria

    5. Ensure the structure is consistent across all questions
       - If there are no explicit sub-parts, create a single part with part_id = ""
       - Every mark must be accounted for in the final JSON structure
       - When marks have special conditions, note them in the criteria field

    Only return valid JSON without any explanation or commentary. Format the JSON neatly with proper indentation.
    """,
    "generation_config": {
        "temperature": 0.2,  # Reduced temperature for more deterministic output
        "top_p": 0.95,
        "max_output_tokens": 8192
    }
}


def preprocess_image(img):
    """Preprocess image to improve text extraction quality."""
    # Convert to grayscale to improve OCR
    if img.mode != 'L':
        img = img.convert('L')

    # Optional: Increase contrast for better text recognition
    # This uses a simple contrast enhancement technique
    from PIL import ImageEnhance
    enhancer = ImageEnhance.Contrast(img)
    img = enhancer.enhance(1.5)  # Increase contrast by 50%

    return img


def create_gemini_content(images, prompt_text=None):
    """Prepares the request payload for Gemini API."""
    if prompt_text is None:
        prompt_text = CONFIGS["prompt"]

    parts = [{"text": prompt_text}]

    if images:
        for img in images:
            # Preprocess image to improve extraction quality
            img = preprocess_image(img)

            buffer = BytesIO()
            img.save(buffer, format="PNG", quality=95)  # Higher quality image
            image_bytes = buffer.getvalue()

            parts.append({
                "inline_data": {
                    "mime_type": "image/png",
                    "data": base64.b64encode(image_bytes).decode('utf-8')
                }
            })

    return {"contents": parts}


def get_gemini_response(content):
    """Sends request to Gemini API and parses response."""
    try:
        model = genai.GenerativeModel(
            model_name="gemini-2.0-flash",
            generation_config=CONFIGS["generation_config"]
        )

        response = model.generate_content(**content)
        cleaned_text = response.text.strip()

        # Improved JSON cleaning for more reliable parsing
        if "```json" in cleaned_text:
            # Extract JSON content from code blocks
            match = re.search(r'```json\s*([\s\S]*?)\s*```', cleaned_text)
            if match:
                cleaned_text = match.group(1).strip()
        else:
            # Clean up any markdown or extra text
            cleaned_text = re.sub(r'```.*?```', '', cleaned_text, flags=re.DOTALL)
            cleaned_text = cleaned_text.strip()

        # Handle common JSON formatting issues
        cleaned_text = cleaned_text.replace('\n            ', ' ').replace('\n        ', ' ').replace('\n    ', ' ')

        try:
            parsed_json = json.loads(cleaned_text)
            return parsed_json
        except json.JSONDecodeError as e:
            print(f"⚠️ JSON Decode Error: {e}")

            # Try to fix common JSON formatting issues
            cleaned_text = re.sub(r',\s*}', '}', cleaned_text)  # Remove trailing commas
            cleaned_text = re.sub(r',\s*]', ']', cleaned_text)  # Remove trailing commas in arrays

            # Last resort: normalize all whitespace
            cleaned_text = cleaned_text.replace('\n', ' ')
            cleaned_text = ' '.join(cleaned_text.split())

            return json.loads(cleaned_text)

    except Exception as e:
        print(f"⚠️ Gemini API error: {e}")
        return None


def validate_response(response):
    """Validates and fixes common issues in the API response."""
    if not response:
        return None

    # Check for expected schema structure
    fixed_response = {}

    for question_key, question_data in response.items():
        # Ensure each question maps to an array of parts
        if not isinstance(question_data, list):
            # If it's not already a list, convert it
            if isinstance(question_data, dict):
                # If it has the old 'parts' structure, extract it
                if 'parts' in question_data:
                    fixed_response[question_key] = question_data['parts']
                else:
                    # Create a single part with the available data
                    part = {
                        "part_id": "",
                        "total_marks": question_data.get("total_marks", 1),
                        "marking_points": []
                    }

                    # Check if there are direct marking points
                    if "marking_points" in question_data:
                        part["marking_points"] = question_data["marking_points"]
                    else:
                        # Try to convert direct properties to a marking point
                        marking_point = {}
                        for k, v in question_data.items():
                            if k not in ["part_id", "total_marks", "marking_points"]:
                                marking_point[k] = v

                        if marking_point:
                            part["marking_points"].append(marking_point)

                    fixed_response[question_key] = [part]
            else:
                # Default to empty array if data is invalid
                fixed_response[question_key] = []
        else:
            # Already in correct format
            fixed_response[question_key] = question_data

    return fixed_response


# Process images from existing directories using Gemini
base_dir = 'input_directory'
output_dir = 'output_directory'
os.makedirs(output_dir, exist_ok=True)

# Log file for tracking processing
log_file = os.path.join(output_dir, "processing_log.txt")
with open(log_file, 'w') as log:
    log.write("Mark Scheme Processing Log\n")
    log.write("=========================\n\n")

# Iterate through all subdirectories in the base directory
for folder_name in os.listdir(base_dir):
    print(f"Processing {folder_name}")
    folder_path = os.path.join(base_dir, folder_name)

    if os.path.isdir(folder_path):
        image_files = []
        for filename in os.listdir(folder_path):
            if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
                image_files.append(os.path.join(folder_path, filename))

        if image_files:
            try:
                # Sort image files to ensure consistent processing order
                image_files.sort()

                # Log the processing
                with open(log_file, 'a') as log:
                    log.write(f"Processing folder: {folder_name}\n")
                    log.write(
                        f"Found {len(image_files)} images: {', '.join(os.path.basename(f) for f in image_files)}\n")

                loaded_images = [Image.open(file) for file in image_files]
                content = create_gemini_content(loaded_images)
                response = get_gemini_response(content)

                if response:
                    # Validate and fix response structure
                    validated_response = validate_response(response)

                    # Save individual JSON response
                    output_file = os.path.join(output_dir, f"{folder_name}.json")
                    with open(output_file, 'w') as f:
                        json.dump(validated_response, f, indent=4)
                    print(f"✅ Gemini response saved for {folder_name}")

                    # Log success
                    with open(log_file, 'a') as log:
                        log.write(f"✅ Successfully processed and saved to {output_file}\n\n")
                else:
                    print(f"❌ Failed to get Gemini response for {folder_name}")
                    # Log failure
                    with open(log_file, 'a') as log:
                        log.write(f"❌ Failed to get Gemini response\n\n")

            except Exception as e:
                print(f"❌ Error processing images in {folder_name}: {e}")
                # Log error
                with open(log_file, 'a') as log:
                    log.write(f"❌ Error: {str(e)}\n\n")

print("✅ All image folders processed successfully!")

# Combine all individual JSON files into one
combined_responses = {}
for json_file in os.listdir(output_dir):
    if json_file.endswith('.json') and json_file != "joint_mark_schemes.json":
        with open(os.path.join(output_dir, json_file), 'r') as f:
            data = json.load(f)
            combined_responses[json_file[:-5]] = data  # Use filename without .json as key

# Save combined responses to a single JSON file
combined_output_file = os.path.join(output_dir, "joint_mark_schemes.json")
with open(combined_output_file, 'w') as f:
    json.dump(combined_responses, f, indent=4)
print(f"✅ Combined responses saved to {combined_output_file}")
