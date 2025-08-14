from io import BytesIO
import logging
from typing import Optional

from google import genai
from google.genai.types import GenerateContentConfig
from PIL import Image

STYLE_PROMPTS = {
    "anime": "Repaint this image in a highly detailed anime style with flat colors, clean outlines, and vibrant tones.",
    "manga": "Convert this image into black-and-white manga art with high contrast, screentone textures,"
    " and fine line work.",
    "oilpainting": "Transform this image into a classic oil painting with visible brush strokes, rich shadows,"
    " and warm tones.",
    "watercolor": "Transform this image into a soft watercolor painting with fluid gradients and delicate outlines.",
    "comic": "Transform this image into colorful Western comic book art with bold outlines and dynamic shading.",
    "cartoon": "Transform this image into a bright cartoon with simplified shapes and playful colors.",
    "sketch": "Transform this image into a pencil sketch with fine crosshatching and realistic shading.",
    "ink": "Transform this image into black ink line art with expressive strokes and no colors.",
    "3d_render": "Transform this image into a realistic 3D render with soft reflections and depth of field.",
    "minimalism": "Transform this image into minimalist art with clean shapes, flat colors, and no unnecessary detail.",
}


class GeminiImageService:
    def __init__(self, api_key: str, logger: logging.Logger, model: str = "gemini-2.0-flash-preview-image-generation"):
        self.model = model
        self.client = genai.Client(api_key=api_key)
        self.logger = logger
        self.base_prompt = (
            "Keep the subject, composition, proportions, and perspective exactly the same as the input image. "
            "Do not add, remove, or move any elements. Maintain the original resolution and framing. "
            "Only change the artistic style as described below.\n\n"
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
