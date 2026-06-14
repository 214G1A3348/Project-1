"""
Hive AI deepfake / AI-generated content detection service.
Uses the v3 endpoint: ai-generated-and-deepfake-content-detection
"""
import httpx
import asyncio
import base64
from typing import Optional
from config import HIVE_API_KEY, HIVE_TIMEOUT_SECONDS
from utils.logger import get_logger

logger = get_logger(__name__)

HIVE_V3_URL = "https://api.thehive.ai/api/v3/hive/ai-generated-and-deepfake-content-detection"


async def analyze_image(
    image_bytes: Optional[bytes] = None,
    image_url: Optional[str] = None,
    filename: str = "image.jpg",
) -> dict:
    """
    Call Hive AI v3 and return a normalised result dict:
    {
        "is_deepfake": bool,
        "confidence":  float,
        "fake_score":  float,
        "real_score":  float,
        "raw_classes": list,
        "status":      "ok" | "error",
        "error_message": str | None
    }
    """

    try:
        if image_bytes:
            headers = {
                "authorization": f"Bearer {HIVE_API_KEY}",
                "accept": "application/json",
            }
            files = {"media": (filename, image_bytes, "image/jpeg")}
            
            async with httpx.AsyncClient(timeout=HIVE_TIMEOUT_SECONDS) as client:
                response = await client.post(HIVE_V3_URL, headers=headers, files=files)
                
        elif image_url:
            headers = {
                "authorization": f"Bearer {HIVE_API_KEY}",
                "Content-Type": "application/json",
                "accept": "application/json",
            }
            payload = {
                "media_metadata": True,
                "input": [{"media_url": image_url}],
            }
            
            async with httpx.AsyncClient(timeout=HIVE_TIMEOUT_SECONDS) as client:
                response = await client.post(HIVE_V3_URL, headers=headers, json=payload)
        else:
            return _error_result("No image bytes or URL provided.")
        response.raise_for_status()
        data = response.json()
        logger.info(f"Hive AI v3 response status: {response.status_code}")
        return _parse_v3_response(data)

    except httpx.TimeoutException:
        logger.error("Hive AI API timed out.")
        return _error_result("Hive AI API request timed out.")
    except httpx.HTTPStatusError as e:
        logger.error(f"Hive AI HTTP error: {e.response.status_code} — {e.response.text[:300]}")
        return _error_result(f"Hive AI HTTP {e.response.status_code}: {e.response.text[:200]}")
    except Exception as e:
        logger.exception("Unexpected error calling Hive AI.")
        return _error_result(str(e))


def _parse_v3_response(data: dict) -> dict:
    """
    Parse the v3 response format:
    {
      "output": [{
        "classes": [
          {"class": "not_ai_generated", "value": 0.999},
          {"class": "ai_generated",     "value": 0.001},
          ...
        ]
      }]
    }
    """
    try:
        classes = data["output"][0]["classes"]
        class_map = {item["class"]: item["value"] for item in classes}

        # Core real vs fake scores
        real_score = class_map.get("not_ai_generated", 0.0)
        ai_score   = class_map.get("ai_generated", 0.0)

        # ALL known AI image generators (Hive returns individual scores per tool)
        ai_image_generators = [
            "dalle", "stablediffusion", "stablediffusioninpaint", "sdxlinpaint",
            "flux", "lcm", "pixart", "glide", "midjourney",
            "bingimagecreator", "adobefirefly", "recraft", "leonardo",
            "luminagpt", "var", "other_image_generators",
        ]
        # Deepfake / video face-swap tools
        deepfake_tools = [
            "liveportrait", "sadtalker", "aniportrait", "makeittalk",
            "hedra", "hallo", "sora", "pika", "haiper", "kling",
            "luma", "runway", "hailuo", "mochi", "hunyuan",
            "cogvideos", "pyramidflows", "mcnet",
        ]

        generator_score = sum(class_map.get(t, 0.0) for t in ai_image_generators)
        deepfake_score  = sum(class_map.get(t, 0.0) for t in deepfake_tools)

        # Combined fake probability — use the higher of:
        # (a) the overall ai_generated class, or
        # (b) sum of individual generator tool scores
        fake_score = min(max(ai_score, generator_score) + deepfake_score, 1.0)

        # Flag as deepfake/AI if fake signal exceeds 5% (lowered from majority-wins)
        is_deepfake = fake_score >= 0.05
        confidence = fake_score if is_deepfake else real_score

        logger.info(f"Hive v3 parsed — real={real_score:.4f} ai={ai_score:.4f} deepfake_tools={deepfake_score:.4f}")

        return {
            "is_deepfake": is_deepfake,
            "confidence":  round(confidence, 4),
            "fake_score":  round(fake_score, 4),
            "real_score":  round(real_score, 4),
            "raw_classes": classes,
            "status":      "ok",
            "error_message": None,
        }
    except (KeyError, IndexError, TypeError) as e:
        logger.error(f"Failed to parse Hive v3 response: {e} | data={str(data)[:300]}")
        return _error_result(f"Unexpected v3 response schema: {e}")


def _error_result(message: str) -> dict:
    return {
        "is_deepfake":   None,
        "confidence":    None,
        "fake_score":    None,
        "real_score":    None,
        "raw_classes":   [],
        "status":        "error",
        "error_message": message,
    }
