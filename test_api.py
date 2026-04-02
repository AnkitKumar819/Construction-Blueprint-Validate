#!/usr/bin/env python3
"""
Test script for the Permit-to-Build Orchestrator API.
Creates a simple test image and sends it to the /validate endpoint.
"""

import requests
from PIL import Image, ImageDraw
import io
import json

def create_test_blueprint():
    """Create a simple test blueprint image."""
    # Create a white image with some basic blueprint elements
    img = Image.new('RGB', (400, 400), color='white')
    draw = ImageDraw.Draw(img)
    
    # Draw some basic shapes to simulate a blueprint
    draw.rectangle([50, 50, 350, 350], outline='blue', width=2)
    draw.rectangle([100, 100, 300, 300], outline='blue', width=2)
    draw.line([50, 50, 350, 350], fill='blue', width=1)
    draw.text((150, 180), "Blueprint", fill='blue')
    
    # Convert to bytes
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='PNG')
    img_bytes.seek(0)
    return img_bytes

def test_validate_endpoint():
    """Test the /validate endpoint."""
    api_url = "http://127.0.0.1:8000/validate"
    
    print("Creating test blueprint image...")
    test_image = create_test_blueprint()
    
    print(f"Sending request to {api_url}...")
    try:
        response = requests.post(
            api_url,
            files={"file": ("test_blueprint.png", test_image, "image/png")}
        )
        
        print(f"\nStatus Code: {response.status_code}")
        print("\nResponse:")
        
        if response.status_code == 200:
            data = response.json()
            print(json.dumps(data, indent=2))
        else:
            print(response.text)
            
    except requests.exceptions.ConnectionError:
        print("❌ Error: Could not connect to the API.")
        print("Make sure the server is running on http://127.0.0.1:8000")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_validate_endpoint()
