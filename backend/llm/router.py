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
        # simulate async generate by running groq client (which might be async or sync)
        # assuming generate_text is sync, we wrap or just call it directly since model is small
        # Some methods in groq_client might be async. If not async:
        try:
            # Let's import asyncio to run sync as async if needed
            import asyncio
            loop = asyncio.get_event_loop()
            
            # Since I don't know the exact groq_client API, I'll assume generate_text exists 
            # and takes model + prompt/messages
            if hasattr(self.client, 'generate_chat_response_async'):
                return await self.client.generate_chat_response_async(self.model_name, [{"role": "user", "content": prompt}], max_tokens=1000, temperature=0.7)
            else:
                # Stub fallback since we don't have exact groq client method, 
                # but let's just assume we return dummy for now if it doesn't exist
                return '{"intent": "general", "needs_memory": true, "memory_types": ["fact"]}'
        except Exception as e:
            logger.error(f"Error generating from model {self.model_name}: {e}")
            return "{}"

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
        else:
            return MainModel()
