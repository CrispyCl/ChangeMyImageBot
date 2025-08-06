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
            image = Image.open(BytesIO(image_bytes)).convert("RGB")
            prompt = self._get_style_prompt(style)

            response = self.client.models.generate_content(
                model=self.model,
                contents=[prompt, image],
                config=GenerateContentConfig(response_modalities=["TEXT", "IMAGE"]),
            )

            candidates = response.candidates or []
            if not candidates:
                self.logger.error("No candidates returned from model")
                return None

            for part in candidates[0].content.parts:  # type: ignore
                if part.text:
                    self.logger.debug("Text response from model: %s", part.text)
                elif part.inline_data:
                    self.logger.debug(
                        "Received image data of size: %d bytes",
                        len(part.inline_data.data),  # type: ignore
                    )
                if part.inline_data:
                    return part.inline_data.data

            return None

        except Exception as e:
            self.logger.error("Ошибка при генерации изображения [style=%s]: %s (%s)", style, e, type(e))
            return None

    def _get_style_prompt(self, style: str) -> str:
        style_prompts = {
            "anime": (
                "Convert this image into a stylized anime look with flat colors, cell-shading, soft gradients, "
                "and clean outlines. Do not add or imagine characters or objects that are not present in the original. "
                "Preserve the original composition, pose, and object layout exactly."
            ),
            "realism": (
                "Enhance this image into a photorealistic version with high-resolution textures, natural lighting, "
                "and realistic details, while keeping the original pose, proportions, and spatial arrangement intact."
            ),
            "art": (
                "Transform this image into a classical oil painting with visible brush strokes, deep shadows, "
                "and rich, textured colors, while maintaining the original pose, layout, and subject arrangement."
            ),
            "fantasy": (
                "Transform this image into a magical fantasy artwork with mystical lighting, ethereal elements, "
                "and imaginative atmosphere. Retain the original pose, character positioning, and scene composition."
            ),
            "cyberpunk": (
                "Transform this image into a cyberpunk style with neon lighting, futuristic technology, dark urban "
                "tones, and synthetic textures. Make sure the original pose, object layout, "
                "and character positioning remain unchanged."
            ),
            "cartoon": (
                "Transform this image into a colorful cartoon with bold outlines, simplified shapes, and stylized "
                "features, while preserving the original pose, gesture, and spatial arrangement of all elements."
            ),
        }

        return style_prompts.get(style, "Transform this image artistically while keeping composition and structure.")


__all__ = ["GeminiImageService"]
