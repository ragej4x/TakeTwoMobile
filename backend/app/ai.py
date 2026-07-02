import json
import logging
import requests
from fastapi import APIRouter, Depends, HTTPException, status
from google import genai
from google.genai import types
from pydantic import BaseModel, HttpUrl

from .deps import get_current_user
from .models import AccountRecord

logger = logging.getLogger(__name__)

router = APIRouter(tags=["ai"])

# Load configuration from raw JSON link
CONFIG_URL = "https://raw.githubusercontent.com/ragej4x/TakeTwoMobile/refs/heads/main/_ai.json"
#GIT = "https://raw.githubusercontent.com/ragej4x/TakeTwoMobile/refs/heads/main/_ai.json"



def load_ai_config():
    """Load AI configuration from remote JSON endpoint."""

    try:
        clean = requests.get(CONFIG_URL)
        clean.raise_for_status()
        git = clean.json()

        response = requests.get(git.get("link"), timeout=5)
        response.raise_for_status()
        config = response.json()

        
        api_key = config.get("google_api_key")
        model_name = config.get("model_name", "gemini-2.5-flash")
        enable_web_search = config.get("enable_web_search", False)
        
        if not api_key:
            logger.error("No API key found in configuration")
            return None, None, False
            
        client = genai.Client(api_key=api_key)
        logger.info(f"AI client initialized successfully with model: {model_name}")
        logger.info(f"Web search enabled: {enable_web_search}")
        return client, model_name, enable_web_search
    except requests.RequestException as e:
        logger.error(f"Failed to load AI config from {CONFIG_URL}: {e}")
        return None, None, False
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in config file: {e}")
        return None, None, False

# Initialize client and model from config
_client, _model_name, _enable_web_search = load_ai_config()

if _client is None:
    logger.warning(
        f"Failed to initialize AI client from {CONFIG_URL} — AI detection will return 503 until configured."
    )


class AnalyzeRequest(BaseModel):
    image_url: HttpUrl
    model_override: str | None = None
    enable_web_search: bool | None = None  # Allow per-request override


class AnalyzeResponse(BaseModel):
    success: bool
    error: str | None = None
    brand: str | None = None
    model: str | None = None
    color: str | None = None
    material: str | None = None
    shoe_type: str | None = None
    condition: str | None = None


SYSTEM_PROMPT = """
You are an AI footwear recognition system.

Your only task is to analyze a single shoe from the provided image.

Return ONLY valid JSON.

Extract only:

- brand
- model
- color
- material
- shoe_type
- condition

Rules:

1. Only analyze footwear.

2. If no shoe is detected return:

{
  "success": false,
  "error": "No shoe detected."
}

3. Never guess.

4. Unknown fields must be "Unknown".

5. Material must be one of:

Leather
Mesh
Knit
Suede
Canvas
Synthetic
Rubber
Mixed
Unknown

6. Shoe type must be one of:

Sneaker
Running
Basketball
Casual
Boot
Sandal
Slipper
Dress
Unknown

7. Condition must be one of:

New
Used
Dirty
Damaged
Unknown

8. Never infer:

- authenticity
- price
- owner
- gender
- age
- release year

9. If multiple shoes appear, analyze the largest visible shoe only.

10. Output ONLY JSON.

Example:

{
    "success": true,
    "brand":"Nike",
    "model":"Air Force 1",
    "color":"White",
    "material":"Leather",
    "shoe_type":"Sneaker",
    "condition":"Used"
}
"""

# Updated system prompt with web search instructions
SYSTEM_PROMPT_WITH_WEBSEARCH = """
You are an AI footwear recognition system.

Your only task is to analyze a single shoe from the provided image.

Return ONLY valid JSON.

Extract only:

- brand
- model
- color
- material
- shoe_type
- condition

Rules:

1. Only analyze footwear.

2. If no shoe is detected return:

{
  "success": false,
  "error": "No shoe detected."
}

3. Never guess.

4. Unknown fields must be "Unknown".

5. Material must be one of:

Leather
Mesh
Knit
Suede
Canvas
Synthetic
Rubber
Mixed
Unknown

6. Shoe type must be one of:

Sneaker
Running
Basketball
Casual
Boot
Sandal
Slipper
Dress
Unknown

7. Condition must be one of:

New
Used
Dirty
Damaged
Unknown

8. Never infer:

- authenticity
- price
- owner
- gender
- age
- release year

9. If multiple shoes appear, analyze the largest visible shoe only.

10. Output ONLY JSON.

11. You have access to web search. Use it to verify and get accurate information about the shoe brand, model, and specifications if needed. When using web search, ensure you cite sources and provide accurate, up-to-date information.

Example:

{
    "success": true,
    "brand":"Nike",
    "model":"Air Force 1",
    "color":"White",
    "material":"Leather",
    "shoe_type":"Sneaker",
    "condition":"Used"
}
"""

RESPONSE_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "success": {"type": "BOOLEAN"},
        "error": {"type": "STRING"},
        "brand": {"type": "STRING"},
        "model": {"type": "STRING"},
        "color": {"type": "STRING"},
        "material": {"type": "STRING"},
        "shoe_type": {"type": "STRING"},
        "condition": {"type": "STRING"},
    },
}


@router.post("/ai/analyze", response_model=AnalyzeResponse)
def analyze(
    req: AnalyzeRequest,
    _current_user: AccountRecord = Depends(get_current_user),
) -> AnalyzeResponse:
    if _client is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI detection is not configured on the server.",
        )

    # Use model override if provided, otherwise use default from config
    model_to_use = req.model_override or _model_name or "gemini-2.5-flash"
    
    # Determine if web search should be enabled
    use_web_search = req.enable_web_search if req.enable_web_search is not None else _enable_web_search
    
    # Select appropriate system prompt
    system_prompt = SYSTEM_PROMPT_WITH_WEBSEARCH if use_web_search else SYSTEM_PROMPT

    try:
        # Download the image from the URL
        logger.info(f"Downloading image from: {req.image_url}")
        image_response = requests.get(str(req.image_url), timeout=15)
        image_response.raise_for_status()
        
        # Determine mime type from Content-Type header or fallback to image/jpeg
        content_type = image_response.headers.get("Content-Type", "image/jpeg")
        
        # Validate that we got an image (basic check)
        if not content_type.startswith("image/"):
            logger.error(f"URL does not point to an image: {content_type}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="The provided URL does not point to a valid image.",
            )
        
        # Get image data
        image_bytes = image_response.content
        
        if len(image_bytes) > 20 * 1024 * 1024:  # 20MB limit
            logger.error(f"Image too large: {len(image_bytes)} bytes")
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="Image is too large. Please use an image under 20MB.",
            )
            
        if len(image_bytes) == 0:
            logger.error("Downloaded empty image")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Downloaded image is empty.",
            )
        
        logger.info(f"Image downloaded successfully: {len(image_bytes)} bytes, type: {content_type}")
        logger.info(f"Web search enabled: {use_web_search}")
        logger.info(f"Using model: {model_to_use}")

        # Prepare the content for Gemini
        contents = [
            types.Part.from_bytes(
                data=image_bytes,
                mime_type=content_type,
            ),
            system_prompt,
        ]

        # Configure generation with web search if enabled
        config_params = {
            "temperature": 0,
            "response_mime_type": "application/json",
            "response_schema": RESPONSE_SCHEMA,
        }
        
        # Add web search tools if enabled
        if use_web_search:
            # Note: Web search requires a specific model that supports it
            # Some models like gemini-2.0-flash-exp support grounding with Google Search
            config_params["tools"] = [
                types.Tool(
                    google_search=types.GoogleSearch()
                )
            ]
            logger.info("Web search tool added to Gemini request")

        # Send to Gemini with web search if enabled
        response = _client.models.generate_content(
            model=model_to_use,
            contents=contents,
            config=types.GenerateContentConfig(**config_params),
        )
        
        logger.info(f"Gemini API request successful with model: {model_to_use}")

    except requests.exceptions.Timeout:
        logger.error(f"Timeout downloading image from: {req.image_url}")
        raise HTTPException(
            status_code=status.HTTP_408_REQUEST_TIMEOUT,
            detail="Timeout downloading image. Please check the URL and try again.",
        )
    except requests.exceptions.ConnectionError:
        logger.error(f"Connection error downloading image from: {req.image_url}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Could not connect to the image URL. Please check the URL.",
        )
    except requests.exceptions.HTTPError as e:
        logger.error(f"HTTP error downloading image: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to download image (HTTP {e.response.status_code}). Please check the URL.",
        )
    except requests.exceptions.RequestException as e:
        logger.error(f"Request error downloading image: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to download image. Please check the URL and try again.",
        )
    except Exception as e:
        logger.exception(f"Gemini shoe analysis request failed with model {model_to_use}")
        
        # Check for specific Gemini API errors
        error_msg = str(e)
        if "401" in error_msg or "UNAUTHENTICATED" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API key. Please check your Google API key configuration.",
            )
        elif "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded. Please try again later.",
            )
        elif "web search" in error_msg.lower() or "grounding" in error_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Web search is not supported by the selected model. Please use a compatible model or disable web search.",
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="AI detection failed. Please try again.",
            )

    try:
        data = json.loads(response.text)
        logger.info(f"Successfully parsed Gemini response")
    except (TypeError, ValueError) as e:
        logger.exception(f"Gemini returned a non-JSON response: {getattr(response, 'text', None)}")
        logger.error(f"Parse error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="AI detection returned an unreadable response.",
        )

    return AnalyzeResponse(**data)


@router.post("/ai/refresh-config")
def refresh_config(_current_user: AccountRecord = Depends(get_current_user)):
    """Refresh the AI configuration from the remote JSON endpoint."""
    global _client, _model_name, _enable_web_search
    _client, _model_name, _enable_web_search = load_ai_config()
    if _client is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Failed to refresh AI configuration.",
        )
    return {
        "status": "Configuration refreshed successfully", 
        "model": _model_name,
        "web_search_enabled": _enable_web_search
    }


@router.get("/ai/status")
def status_check():
    """Check the status of the AI configuration."""
    return {
        "configured": _client is not None,
        "model": _model_name,
        "config_url": CONFIG_URL,
        "web_search_enabled": _enable_web_search
    }