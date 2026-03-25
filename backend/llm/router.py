from utils.groq_client import GroqClient
import logging
logger = logging.getLogger(__name__)

class GenericModel:
    def __init__(self, model_name: str):
        self.model_name = model_name
        self.client = None
        try:
            self.client = GroqClient()
        except:
            pass

    async def generate(self, prompt: str) -> str:
        if not self.client:
            return ""
        try:
            import asyncio

            # Prefer native async method when available.
            if hasattr(self.client, 'generate_chat_response_async'):
                return await self.client.generate_chat_response_async(self.model_name, [{"role": "user", "content": prompt}], max_tokens=1000, temperature=0.7)

            # Current GroqClient implementation is sync; run it in a thread so callers stay async.
            if hasattr(self.client, 'generate_content'):
                try:
                    return await asyncio.to_thread(
                        self.client.generate_content,
                        prompt,
                        model_id=self.model_name,
                    )
                except TypeError:
                    # Backward-compatible fallback for older generate_content signatures.
                    return await asyncio.to_thread(self.client.generate_content, prompt)

            if hasattr(self.client, 'generate_text'):
                return await asyncio.to_thread(self.client.generate_text, prompt)

            logger.warning("No compatible generation method found on GroqClient")
            return "I'm ready to help. Could you share a bit more detail so I can give a precise answer?"
        except Exception as e:
            logger.error(f"Error generating from model {self.model_name}: {e}")
            return "I ran into a temporary issue while generating that response. Please try again."

class FastModel(GenericModel):
    def __init__(self):
        super().__init__("llama-3.1-8b-instant")

class MidModel(GenericModel):
    def __init__(self):
        super().__init__("llama-3.3-70b-versatile")

class MainModel:
    async def generate(self, prompt: str) -> str:
        # Instead of wrapping the complex orchestrator here for the main response,
        # we can just use the versatile model or delegator
        m = GenericModel("llama-3.3-70b-versatile")
        return await m.generate(prompt)

class LLMRouter:
    def get_model(self, model_type: str):
        if model_type == "fast":
            return FastModel()
        elif model_type == "mid":
            return MidModel()
        elif model_type in ("main", "conversation"):
            return MainModel()
        elif model_type == "code":
            return GenericModel("llama-3.1-8b-instant")
        elif model_type == "reasoning":
            return GenericModel("deepseek-r1-distill-llama-70b")
        elif model_type == "summarization":
            return GenericModel("mixtral-8x7b-32k")
        else:
            return MainModel()
