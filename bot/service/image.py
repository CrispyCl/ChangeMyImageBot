from io import BytesIO
import logging
from typing import Optional

from google import genai
from google.genai.types import GenerateContentConfig
from PIL import Image


class GeminiImageService:
    def __init__(self, api_key: str, logger: logging.Logger, model: str = "gemini-2.0-flash-preview-image-generation"):
        self.model = model
        self.client = genai.Client(api_key=api_key)
        self.logger = logger

    async def transform_image(self, image_bytes: bytes, style: str) -> Optional[bytes]:
        """Преобразует изображение в указанный стиль и возвращает сгенерированное изображение (bytes)"""

        try:
            image = Image.open(BytesIO(image_bytes))
            prompt = self._get_style_prompt(style)

            response = self.client.models.generate_content(
                model=self.model,
                contents=[prompt, image],
                config=GenerateContentConfig(response_modalities=["TEXT", "IMAGE"]),
            )

            for part in response.candidates[0].content.parts:  # type: ignore
                if part.inline_data:
                    return part.inline_data.data

            return None

        except Exception as e:
            self.logger.error("Ошибка при генерации изображения: %s (%s)", e, type(e))
            return None

    def _get_style_prompt(self, style: str) -> str:
        style_prompts = {
            "anime": "Transform this image into anime style with cel-shading, "
            "clean lines, expressive eyes, and vibrant colors.",
            "realism": "Enhance this image into a photorealistic version with professional lighting and textures.",
            "art": "Transform this image into a classical oil painting with brush strokes and rich colors.",
            "fantasy": "Transform this image into a fantasy artwork with magical atmosphere and mystical elements.",
            "cyberpunk": "Transform this image into cyberpunk style with neon "
            "lights, futuristic details, and dark tones.",
            "cartoon": "Transform this image into a cartoon with bold colors and simplified features.",
        }

        return style_prompts.get(style, "Transform this image artistically while keeping composition and structure.")


__all__ = ["GeminiImageService"]
