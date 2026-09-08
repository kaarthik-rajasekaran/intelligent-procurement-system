from abc import ABC, abstractmethod
from typing import Optional, List
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)


class BaseLLMProvider(ABC):
    @abstractmethod
    def generate_text(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        pass

    @abstractmethod
    def generate_embedding(self, text: str) -> List[float]:
        pass

    @abstractmethod
    def health_check(self) -> bool:
        pass


# ---------------------------------------------------------------------------
# MOCK LOCAL PROVIDER  (zero dependencies — always available)
# ---------------------------------------------------------------------------
class MockLocalLLMProvider(BaseLLMProvider):
    """
    Deterministic mock LLM for local testing without any API credentials.
    """

    def generate_text(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        prompt_lower = prompt.lower()
        if "summarize" in prompt_lower or "summary" in prompt_lower:
            return (
                "**Executive PR Summary:**\n"
                "This procurement request has been structured with verified specifications. "
                "The requested quantity has been evaluated against current stock reserves, and active vendor rankings "
                "have been calculated using multi-criteria weighted scoring (Quality, Delivery, and Price). "
                "Proceeding with the recommended vendor optimizes both delivery lead time and budgetary variance."
            )
        elif "explain vendor" in prompt_lower or "recommendation" in prompt_lower:
            return (
                "**Vendor Recommendation Rationale:**\n"
                "The system evaluated eligible suppliers using calibrated performance metrics. "
                "The top-ranked vendor demonstrated superior reliability (94% on-time fulfillment) and holds "
                "active quality badges. While alternative suppliers may offer nominal price discounts, the risk of "
                "operational delay is significantly lower with the recommended vendor."
            )
        elif "quotation" in prompt_lower or "comparison" in prompt_lower:
            return (
                "**Quotation Evaluation Analysis:**\n"
                "The competitive bidding evaluation balances cost (40%), lead time (20%), reliability (20%), and quality (20%). "
                "The top candidate offers optimal trade-offs between unit cost and fulfillment velocity. "
                "If overriding this recommendation, ensure a substantive business justification is documented."
            )
        else:
            return (
                "**Procurement Copilot:**\n"
                f"I have reviewed your inquiry regarding: '{prompt[:100]}...'. "
                "All procurement actions are governed by corporate policy compliance, inventory availability checks, "
                "and supervisor review thresholds. Let me know if you need specific analytical breakdowns."
            )

    def generate_embedding(self, text: str) -> List[float]:
        import hashlib
        import numpy as np
        seed = int(hashlib.md5(text.encode("utf-8")).hexdigest()[:8], 16)
        rng = np.random.default_rng(seed)
        vec = rng.standard_normal(64)
        norm = float(sum(x ** 2 for x in vec) ** 0.5)
        if norm > 0:
            vec = [x / norm for x in vec]
        return list(vec)

    def health_check(self) -> bool:
        return True


# ---------------------------------------------------------------------------
# GOOGLE GEMINI PROVIDER (new google-genai SDK)
# ---------------------------------------------------------------------------
class GeminiLLMProvider(BaseLLMProvider):
    """
    Google Gemini via the new google-genai SDK.
    """

    def __init__(self, api_key: str, model: str = "gemini-flash-lite-latest"):
        try:
            from google import genai
            from google.genai import types as genai_types
            self._client = genai.Client(api_key=api_key)
            self._genai_types = genai_types
            self._model_name = model or "gemini-flash-lite-latest"
            self._fallback_models = [
                "gemini-flash-lite-latest",
                "gemini-3.5-flash",
                "gemini-flash-latest",
                "gemini-3.5-flash-lite"
            ]
            logger.info(f"[LLM] Gemini provider initialized with primary model: {self._model_name}")
        except ImportError:
            raise RuntimeError(
                "google-genai package not installed. "
                "Run: pip install google-genai"
            )

    def generate_text(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        candidate_models = [self._model_name] + [m for m in self._fallback_models if m != self._model_name]
        last_error = None

        for model_candidate in candidate_models:
            try:
                config = None
                if system_prompt:
                    config = self._genai_types.GenerateContentConfig(
                        system_instruction=system_prompt,
                        temperature=0.3
                    )
                else:
                    config = self._genai_types.GenerateContentConfig(
                        temperature=0.3
                    )

                response = self._client.models.generate_content(
                    model=model_candidate,
                    contents=prompt,
                    config=config
                )
                if response and response.text:
                    return response.text.strip()
            except Exception as e:
                last_error = e
                logger.warning(f"[Gemini] model '{model_candidate}' failed: {e}. Trying fallback...")
                continue

        logger.error(f"[Gemini] All Gemini candidate models failed ({last_error}). Falling back to analytical mock response.")
        return MockLocalLLMProvider().generate_text(prompt, system_prompt)

    def generate_embedding(self, text: str) -> List[float]:
        for em in ["gemini-embedding-001", "gemini-embedding-2"]:
            try:
                result = self._client.models.embed_content(
                    model=em,
                    contents=text
                )
                if result and result.embeddings:
                    return list(result.embeddings[0].values)
            except Exception as e:
                logger.warning(f"[Gemini] Embedding model '{em}' failed: {e}")
                continue

        logger.warning("[Gemini] All embedding models failed, using deterministic local embedding fallback.")
        return MockLocalLLMProvider().generate_embedding(text)

    def health_check(self) -> bool:
        try:
            response = self._client.models.generate_content(
                model=self._model_name,
                contents="OK",
                config=self._genai_types.GenerateContentConfig(temperature=0.1)
            )
            return bool(response.text)
        except Exception:
            return False


# ---------------------------------------------------------------------------
# OPENAI PROVIDER
# ---------------------------------------------------------------------------
class OpenAILLMProvider(BaseLLMProvider):
    """
    OpenAI ChatCompletion via openai SDK.
    Requires: pip install openai
    """

    def __init__(self, api_key: str, model: str = "gpt-4o-mini"):
        try:
            from openai import OpenAI
            self._client = OpenAI(api_key=api_key)
            self._model = model
            logger.info(f"[LLM] OpenAI provider initialized with model: {model}")
        except ImportError:
            raise RuntimeError("openai package not installed. Run: pip install openai")

    def generate_text(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        try:
            resp = self._client.chat.completions.create(
                model=self._model,
                messages=messages,
                max_tokens=1024,
                temperature=0.3
            )
            return resp.choices[0].message.content or ""
        except Exception as e:
            logger.error(f"[OpenAI] generate_text error: {e}")
            raise

    def generate_embedding(self, text: str) -> List[float]:
        try:
            resp = self._client.embeddings.create(
                model="text-embedding-3-small",
                input=text[:8000]
            )
            return resp.data[0].embedding
        except Exception as e:
            logger.warning(f"[OpenAI] Embedding failed, using fallback: {e}")
            return MockLocalLLMProvider().generate_embedding(text)

    def health_check(self) -> bool:
        try:
            resp = self._client.chat.completions.create(
                model=self._model,
                messages=[{"role": "user", "content": "ping"}],
                max_tokens=5
            )
            return bool(resp.choices)
        except Exception:
            return False


# ---------------------------------------------------------------------------
# ANTHROPIC PROVIDER
# ---------------------------------------------------------------------------
class AnthropicLLMProvider(BaseLLMProvider):
    """
    Anthropic Claude via anthropic SDK.
    Requires: pip install anthropic
    """

    def __init__(self, api_key: str, model: str = "claude-3-haiku-20240307"):
        try:
            import anthropic
            self._client = anthropic.Anthropic(api_key=api_key)
            self._model = model
            logger.info(f"[LLM] Anthropic provider initialized with model: {model}")
        except ImportError:
            raise RuntimeError("anthropic package not installed. Run: pip install anthropic")

    def generate_text(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        try:
            resp = self._client.messages.create(
                model=self._model,
                max_tokens=1024,
                system=system_prompt or "You are an intelligent procurement assistant.",
                messages=[{"role": "user", "content": prompt}]
            )
            return resp.content[0].text
        except Exception as e:
            logger.error(f"[Anthropic] generate_text error: {e}")
            raise

    def generate_embedding(self, text: str) -> List[float]:
        # Anthropic does not expose an embedding API; fall back to mock
        return MockLocalLLMProvider().generate_embedding(text)

    def health_check(self) -> bool:
        try:
            resp = self._client.messages.create(
                model=self._model,
                max_tokens=5,
                messages=[{"role": "user", "content": "ping"}]
            )
            return bool(resp.content)
        except Exception:
            return False


# ---------------------------------------------------------------------------
# FACTORY
# ---------------------------------------------------------------------------
def get_llm_provider() -> BaseLLMProvider:
    """
    Returns the configured LLM provider based on LLM_PROVIDER setting.
    Falls back to MockLocalLLMProvider if no valid provider is configured
    or if the required package is not installed.
    """
    provider_name = settings.LLM_PROVIDER.lower().strip()

    if provider_name == "gemini" and settings.GEMINI_API_KEY:
        try:
            return GeminiLLMProvider(
                api_key=settings.GEMINI_API_KEY,
                model=settings.GEMINI_MODEL
            )
        except Exception as e:
            logger.warning(f"[LLM] Gemini init failed: {e}. Falling back to mock.")

    elif provider_name == "openai" and settings.OPENAI_API_KEY:
        try:
            return OpenAILLMProvider(
                api_key=settings.OPENAI_API_KEY,
                model=settings.OPENAI_MODEL
            )
        except Exception as e:
            logger.warning(f"[LLM] OpenAI init failed: {e}. Falling back to mock.")

    elif provider_name == "anthropic" and settings.ANTHROPIC_API_KEY:
        try:
            return AnthropicLLMProvider(
                api_key=settings.ANTHROPIC_API_KEY,
                model=settings.ANTHROPIC_MODEL
            )
        except Exception as e:
            logger.warning(f"[LLM] Anthropic init failed: {e}. Falling back to mock.")

    elif provider_name != "mock_local":
        logger.warning(
            f"[LLM] Unknown provider '{provider_name}' or missing API key. "
            "Falling back to MockLocalLLMProvider."
        )

    logger.info("[LLM] Using MockLocalLLMProvider (no real API key configured).")
    return MockLocalLLMProvider()
