from io import BytesIO
import logging
from typing import Optional

from google import genai
from google.genai.types import GenerateContentConfig
from PIL import Image

STYLE_PROMPTS = {
    "anime": "Apply anime style ONLY as visual filter. Preserve EXACT composition, subjects, and perspective. "
    "Use flat colors, clean outlines, vibrant tones. NO added/removed elements, NO content changes.",
    "manga": "Apply manga style ONLY as visual filter. Preserve EXACT composition, subjects, and perspective. "
    "Convert to black-white with high contrast, screentones. NO content changes, NO added details.",
    "oilpainting": "Apply oil painting style ONLY as visual filter. Preserve EXACT composition. "
    "Use visible brush strokes, rich shadows, warm tones. NO added/removed elements.",
    "watercolor": "Apply watercolor style ONLY as visual filter. Preserve EXACT composition. "
    "Use fluid gradients, delicate outlines, soft blending. NO structural changes.",
    "comic": "Apply Western comic style ONLY as visual filter. Preserve EXACT composition. "
    "Use bold outlines, dynamic shading, vibrant colors. NO added elements.",
    "cartoon": "Apply cartoon style ONLY as visual filter. Preserve EXACT composition. "
    "Use simplified shapes, playful colors, clean lines. NO position changes.",
    "isometric": "Apply isometric game art style ONLY as visual filter. Preserve EXACT composition. "
    "Use clean geometry, soft lighting, consistent angles. NO perspective changes.",
    "sketch": "Apply pencil sketch style ONLY as visual filter. Preserve EXACT composition. "
    "Use fine crosshatching, realistic shading, grayscale. NO added details.",
    "ink": "Apply ink line art style ONLY as visual filter. Preserve EXACT composition. "
    "Use expressive strokes, black-white only, no colors. NO element modifications.",
    "3d_render": "Apply 3D render style ONLY as visual filter. Preserve EXACT composition. "
    "Use soft reflections, depth of field, realistic lighting. NO model changes.",
    "minimalism": "Apply minimalist style ONLY as visual filter. Preserve EXACT composition. "
    "Use clean shapes, flat colors, reduced details. NO element removal/addition.",
}


class GeminiImageService:
    def __init__(self, api_key: str, logger: logging.Logger, model: str = "gemini-2.0-flash-preview-image-generation"):
        self.model = model
        self.client = genai.Client(api_key=api_key)
        self.logger = logger
        self.base_prompt = (
            "STRICTLY apply requested style as visual filter ONLY. "
            "PRESERVE EXACTLY: composition, subjects, perspective, details. "
            "DO NOT: add/remove elements, change positions, generate new content. "
            "OUTPUT: Stylized version of input image."
        )

    async def transform_image(
        self,
        image_bytes: bytes,
        style: str,
        custom_prompt: Optional[str] = None,
    ) -> Optional[bytes]:
        """Преобразует изображение в указанный стиль и возвращает сгенерированное изображение (bytes)"""

        try:
            image = Image.open(BytesIO(image_bytes)).convert("RGB")
            prompt = self._get_style_prompt(style=style, custom_prompt=custom_prompt)

            response = self.client.models.generate_content(
                model=self.model,
                contents=[prompt, image],
                config=GenerateContentConfig(response_modalities=["TEXT", "IMAGE"]),
            )

            candidates = response.candidates or []

            for candidate in candidates:
                if not candidate.content:
                    continue
                parts = candidate.content.parts or []
                for part in parts:
                    if part.inline_data:
                        self.logger.debug("Received image: %d bytes", len(part.inline_data.data or []))
                        return part.inline_data.data

            self.logger.error("No image data in response. Candidates: %d", len(candidates))
            return None

        except Exception as e:
            self.logger.error("Ошибка при генерации изображения [style=%s]: %s (%s)", style, e, type(e))
            return None

    def _get_style_prompt(self, style: str, custom_prompt: Optional[str] = None) -> str:
        parts = [self.base_prompt]

        if custom_prompt:
            parts.append(custom_prompt)
        else:
            style_prompt = STYLE_PROMPTS.get(style.lower())
            if style_prompt:
                parts.append(style_prompt)
            else:
                parts.append(f"Apply {style} style filter while preserving original content exactly.")

        return "\n\n".join(parts)


__all__ = ["GeminiImageService"]
