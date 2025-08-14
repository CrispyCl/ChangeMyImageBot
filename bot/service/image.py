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
    "realism": "Convert this image into a photorealistic version with detailed textures, natural lighting,"
    " and realistic proportions.",
    "oilpainting": "Transform this image into a classic oil painting with visible brush strokes, rich shadows,"
    " and warm tones.",
    "watercolor": "Transform this image into a soft watercolor painting with fluid gradients and delicate outlines.",
    "pixelart": "Transform this image into retro pixel art with a small, consistent color palette and visible"
    " pixel edges.",
    "fantasy": "Transform this image into a magical fantasy artwork with glowing accents and mystical atmosphere.",
    "cyberpunk": "Transform this image into a cyberpunk scene with neon lighting, futuristic elements,"
    " and dark urban tones.",
    "steampunk": "Transform this image into steampunk style with brass textures, gears, steam effects,"
    " and Victorian aesthetics.",
    "gothic": "Transform this image into gothic art with dark tones, ornate patterns, and dramatic lighting.",
    "synthwave": "Transform this image into a synthwave style with neon grids, purple-orange gradients,"
    " and 80s retro-futurism.",
    "comic": "Transform this image into colorful Western comic book art with bold outlines and dynamic shading.",
    "cartoon": "Transform this image into a bright cartoon with simplified shapes and playful colors.",
    "isometric": "Transform this image into isometric game art with clean geometry and soft lighting.",
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
            if not candidates:
                self.logger.error("No candidates returned from model")
                return None

            if not candidates[0].content:
                self.logger.error("No content into the candidate[0]")
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

    def _get_style_prompt(self, style: str, custom_prompt: Optional[str] = None) -> str:
        base_instruction = (
            "Keep the subject, composition, proportions, and perspective exactly the same as the input image. "
            "Do not add, remove, or move any elements. Maintain the original resolution and framing. "
            "Only change the artistic style as described below.\n\n"
        )
        if custom_prompt:
            return base_instruction + custom_prompt

        style_description = STYLE_PROMPTS.get(style.lower())
        if style_description:
            return base_instruction + style_description

        return base_instruction + "Apply an artistic transformation keeping all original layout and structure."


__all__ = ["GeminiImageService"]
