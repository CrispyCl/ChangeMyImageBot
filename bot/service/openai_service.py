import base64
import logging
from typing import Optional

import aiohttp
import openai


class OpenAIService:
    def __init__(self, api_key: str, logger: logging.Logger, model: str = "gpt-4o"):
        self.client = openai.OpenAI(api_key=api_key)
        self.model = model
        self.logger = logger

    async def transform_image(self, image_url: str, style: str) -> Optional[str]:
        """Преобразует изображение в выбранный стиль используя новый Responses API"""
        try:
            image_data = await self._download_image(image_url)
            if not image_data:
                return None

            base64_image = base64.b64encode(image_data).decode("utf-8")
            style_prompt = self._get_style_prompt(style)

            response = self.client.responses.create(
                model=self.model,
                input=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "input_text", "text": style_prompt},
                            {
                                "type": "input_image",
                                "image_url": f"data:image/jpeg;base64,{base64_image}",
                            },
                        ],
                    },  # type: ignore
                ],
                tools=[
                    {
                        "type": "image_generation",
                        "quality": "high",
                        "size": "1024x1024",
                        "background": "auto",
                    },
                ],
            )
            if response.error:
                self.logger.error(f"Error creating image: {response.error}")

            image_generation_calls = [output for output in response.output if output.type == "image_generation_call"]

            if image_generation_calls:
                image_base64 = image_generation_calls[0].result
                return await self._upload_image_from_base64(str(image_base64))

            return None

        except Exception as e:
            self.logger.error(f"Error transforming image: {e}")
            return None

    async def _download_image(self, image_url: str) -> Optional[bytes]:
        """Скачивает изображение по URL"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(image_url) as response:
                    if response.status == 200:
                        return await response.read()
            return None
        except Exception as e:
            self.logger.error(f"Error downloading image: {e}")
            return None

    async def _create_file(self, file_data: bytes, filename: str) -> Optional[str]:
        """Создает файл через Files API и возвращает file_id"""
        try:
            import tempfile
            import os

            with tempfile.NamedTemporaryFile(delete=False, suffix=f"_{filename}") as temp_file:
                temp_file.write(file_data)
                temp_file_path = temp_file.name

            try:
                with open(temp_file_path, "rb") as f:  # noqa
                    file_response = self.client.files.create(file=f, purpose="vision")
                return file_response.id
            finally:
                os.unlink(temp_file_path)  # noqa

        except Exception as e:
            self.logger.error(f"Error creating file: {e}")
            return None

    async def _upload_image_from_base64(self, base64_image: str) -> Optional[str]:
        """Загружает изображение из base64 и возвращает URL"""
        try:
            return f"data:image/png;base64,{base64_image}"
        except Exception as e:
            self.logger.error(f"Error uploading image: {e}")
            return None

    def _get_style_prompt(self, style: str) -> str:
        """Возвращает промпт для преобразования в выбранный стиль"""
        style_prompts = {
            "anime": (
                "Transform this image into anime/manga art style while maintaining the exact same composition, "
                "poses, and layout.\nApply cel-shading, vibrant colors, large expressive eyes, clean line art, and "
                "Japanese animation aesthetics.\nKeep all objects and people in their original positions."
            ),
            "realism": (
                "Enhance this image with photorealistic details while maintaining the exact same composition and "
                "poses.\nImprove lighting, add realistic textures, enhance details, and make it look like professional "
                "photography.\nKeep all elements in their original positions."
            ),
            "art": (
                "Transform this image into a classical painting style while maintaining the exact same composition and "
                "poses.\nApply artistic brush strokes, rich colors, oil painting textures, and fine art aesthetics.\n"
                "Keep all objects and people in their original positions."
            ),
            "fantasy": (
                "Transform this image into fantasy art style while maintaining the exact same composition and poses.\n"
                "Add magical atmosphere, mystical lighting, ethereal glow, enchanted elements, and fantasy aesthetics."
                "\nKeep all objects and people in their original positions."
            ),
            "cyberpunk": (
                "Transform this image into cyberpunk style while maintaining the exact same composition and poses.\n"
                "Add neon lighting, futuristic technology, dark atmosphere, electric blue and pink colors, and sci-fi "
                "elements.\nKeep all objects and people in their original positions."
            ),
            "cartoon": (
                "Transform this image into cartoon/animated style while maintaining the exact same composition and "
                "poses.\nApply bold colors, simplified features, clean outlines, and playful cartoon aesthetics.\n"
                "Keep all objects and people in their original positions."
            ),
        }

        return style_prompts.get(
            style,
            "Transform this image with artistic enhancement while maintaining the exact same composition and poses.",
        )

    async def analyze_image(self, image_url: str) -> Optional[str]:
        """Анализирует изображение и возвращает его описание"""
        try:
            image_data = await self._download_image(image_url)
            if not image_data:
                return None

            base64_image = base64.b64encode(image_data).decode("utf-8")

            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": (
                                    "Describe this image in detail, focusing on composition, poses, objects, and their "
                                    "positions."
                                ),
                            },
                            {
                                "type": "image_url",
                                "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"},
                            },
                        ],
                    },
                ],
                max_tokens=300,
            )

            return response.choices[0].message.content

        except Exception as e:
            self.logger.error(f"Error analyzing image: {e}")
            return None


__all__ = ["OpenAIService"]
