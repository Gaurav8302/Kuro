"""LLM provider errors shared by the chat path."""


class LLMProviderError(Exception):
    """Raised when all configured model attempts fail.

    This must never be converted into a fake assistant message.
    """

    def __init__(self, message: str, *, model: str | None = None, status_code: int = 502):
        super().__init__(message)
        self.model = model
        self.status_code = status_code
        self.public_message = "The AI provider failed to generate a response. Please try again."
