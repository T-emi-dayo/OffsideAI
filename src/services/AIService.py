from typing import Any, Dict, Iterator, AsyncIterator, Optional, Type
from pydantic import BaseModel
from langchain.chat_models import init_chat_model
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_google_genai import GoogleGenerativeAIEmbeddings

from src.config.settings import settings


class AIResponse(BaseModel):
    """Unified response schema for all AIService methods."""
    content: Optional[str] = None
    parsed: Optional[Any] = None
    tool_calls: Optional[list[dict]] = None
    model: Optional[str] = None
    usage_metadata: Optional[Dict[str, int]] = None
    parsing_error: Optional[str] = None


class AIService:
    # Class-level caches: shared across all instances so models are never
    # re-initialized when multiple agents each create their own AIService().
    _model_cache: dict = {}
    _embedder: Optional[GoogleGenerativeAIEmbeddings] = None

    def _get_cached_model(self, model_name: str, temperature: float,
                          model_provider: str, max_retries: int = 2):
        key = (model_name, temperature, model_provider, max_retries)
        if key not in AIService._model_cache:
            AIService._model_cache[key] = init_chat_model(
                model=model_name,
                model_provider=model_provider,
                temperature=temperature,
                api_key=settings.GEMINI_API_KEY,
                max_retries=max_retries,
            )
        return AIService._model_cache[key]

    def _extract_usage(self, response: AIMessage) -> Optional[Dict[str, int]]:
        meta = getattr(response, "usage_metadata", None)
        if not meta:
            return None
        # LangChain UsageMetadata may be a TypedDict or a plain object depending
        # on the version — handle both access patterns.
        if isinstance(meta, dict):
            return {
                "input_tokens": meta.get("input_tokens", 0),
                "output_tokens": meta.get("output_tokens", 0),
                "total_tokens": meta.get("total_tokens", 0),
            }
        return {
            "input_tokens": getattr(meta, "input_tokens", 0),
            "output_tokens": getattr(meta, "output_tokens", 0),
            "total_tokens": getattr(meta, "total_tokens", 0),
        }

    def _extract_tool_calls(self, response: AIMessage) -> Optional[list[dict]]:
        calls = getattr(response, "tool_calls", None)
        if not calls:
            return None
        return [
            {"name": c.get("name"), "args": c.get("args", {}), "id": c.get("id")}
            for c in calls
        ]

    def _build_response(self, response: AIMessage, usage_metadata: bool = False) -> AIResponse:
        model_name = None
        if response.response_metadata:
            model_name = response.response_metadata.get("model_name")
        return AIResponse(
            content=response.content or None,
            tool_calls=self._extract_tool_calls(response),
            model=model_name,
            usage_metadata=self._extract_usage(response) if usage_metadata else None,
        )

    def _build_structured_response(self, result: Any, usage_metadata: bool) -> AIResponse:
        """Shared response builder for invoke_structured / ainvoke_structured."""
        if not usage_metadata:
            return AIResponse(parsed=result)
        raw: AIMessage = result["raw"]
        parsing_error = result.get("parsing_error")
        return AIResponse(
            parsed=result.get("parsed"),
            tool_calls=self._extract_tool_calls(raw),
            model=raw.response_metadata.get("model_name") if raw.response_metadata else None,
            usage_metadata=self._extract_usage(raw),
            parsing_error=str(parsing_error) if parsing_error else None,
        )

    # -------------------------------------------------------------------------
    # Model factories
    # -------------------------------------------------------------------------

    def get_chat_model(self, model_name: str = settings.BASE_MODEL,
                       temperature: float = settings.BASE_TEMPERATURE,
                       model_provider: str = settings.BASE_MODEL_PROVIDER,
                       max_retries: int = 2):
        return self._get_cached_model(model_name, temperature, model_provider, max_retries)

    def get_model_with_fallback(self, fallback_model: str,
                                model_name: str = settings.BASE_MODEL,
                                temperature: float = settings.BASE_TEMPERATURE,
                                model_provider: str = settings.BASE_MODEL_PROVIDER,
                                max_retries: int = 2):
        primary = self._get_cached_model(model_name, temperature, model_provider, max_retries)
        fallback = self._get_cached_model(fallback_model, temperature, model_provider, max_retries)
        return primary.with_fallbacks([fallback])

    # -------------------------------------------------------------------------
    # Message builder
    # -------------------------------------------------------------------------

    def build_messages(self, user: str, system: Optional[str] = None,
                       history: Optional[list[dict]] = None) -> list:
        messages = []
        if system:
            messages.append(SystemMessage(content=system))
        for msg in (history or []):
            role = msg.get("role")
            content = msg.get("content", "")
            if role == "user":
                messages.append(HumanMessage(content=content))
            elif role == "assistant":
                messages.append(AIMessage(content=content))
        messages.append(HumanMessage(content=user))
        return messages

    # -------------------------------------------------------------------------
    # Invoke — plain text, optionally with bound tools (sync / async)
    # -------------------------------------------------------------------------

    def invoke(self, messages, model_name: str = settings.BASE_MODEL,
               temperature: float = settings.BASE_TEMPERATURE,
               model_provider: str = settings.BASE_MODEL_PROVIDER,
               tools: Optional[list] = None,
               usage_metadata: bool = False, **kwargs) -> AIResponse:
        llm = self._get_cached_model(model_name, temperature, model_provider)
        if tools:
            llm = llm.bind_tools(tools)
        response = llm.invoke(messages)
        return self._build_response(response, usage_metadata)

    async def ainvoke(self, messages, model_name: str = settings.BASE_MODEL,
                      temperature: float = settings.BASE_TEMPERATURE,
                      model_provider: str = settings.BASE_MODEL_PROVIDER,
                      tools: Optional[list] = None,
                      usage_metadata: bool = False, **kwargs) -> AIResponse:
        llm = self._get_cached_model(model_name, temperature, model_provider)
        if tools:
            llm = llm.bind_tools(tools)
        response = await llm.ainvoke(messages)
        return self._build_response(response, usage_metadata)

    # -------------------------------------------------------------------------
    # Structured output — schema required, tools optional (sync / async)
    # -------------------------------------------------------------------------

    def invoke_structured(self, messages, schema: Type[BaseModel],
                          tools: Optional[list] = None,
                          model_name: str = settings.BASE_MODEL,
                          temperature: float = settings.BASE_TEMPERATURE,
                          model_provider: str = settings.BASE_MODEL_PROVIDER,
                          usage_metadata: bool = False, **kwargs) -> AIResponse:
        llm = self._get_cached_model(model_name, temperature, model_provider)
        if tools:
            llm = llm.bind_tools(tools)
        structured_llm = llm.with_structured_output(schema=schema, include_raw=usage_metadata)
        result = structured_llm.invoke(messages)
        return self._build_structured_response(result, usage_metadata)

    async def ainvoke_structured(self, messages, schema: Type[BaseModel],
                                 tools: Optional[list] = None,
                                 model_name: str = settings.BASE_MODEL,
                                 temperature: float = settings.BASE_TEMPERATURE,
                                 model_provider: str = settings.BASE_MODEL_PROVIDER,
                                 usage_metadata: bool = False, **kwargs) -> AIResponse:
        llm = self._get_cached_model(model_name, temperature, model_provider)
        if tools:
            llm = llm.bind_tools(tools)
        structured_llm = llm.with_structured_output(schema=schema, include_raw=usage_metadata)
        result = await structured_llm.ainvoke(messages)
        return self._build_structured_response(result, usage_metadata)

    # -------------------------------------------------------------------------
    # Streaming — yields non-empty content chunks (sync / async)
    # -------------------------------------------------------------------------

    def stream(self, messages, model_name: str = settings.BASE_MODEL,
               temperature: float = settings.BASE_TEMPERATURE,
               model_provider: str = settings.BASE_MODEL_PROVIDER,
               **kwargs) -> Iterator[str]:
        llm = self._get_cached_model(model_name, temperature, model_provider)
        for chunk in llm.stream(messages):
            if chunk.content:
                yield chunk.content

    async def astream(self, messages, model_name: str = settings.BASE_MODEL,
                      temperature: float = settings.BASE_TEMPERATURE,
                      model_provider: str = settings.BASE_MODEL_PROVIDER,
                      **kwargs) -> AsyncIterator[str]:
        llm = self._get_cached_model(model_name, temperature, model_provider)
        async for chunk in llm.astream(messages):
            if chunk.content:
                yield chunk.content

    # -------------------------------------------------------------------------
    # Batch (sync / async)
    # -------------------------------------------------------------------------

    def batch_invoke(self, prompts: list[str],
                     model_name: str = settings.BASE_MODEL,
                     temperature: float = settings.BASE_TEMPERATURE,
                     model_provider: str = settings.BASE_MODEL_PROVIDER,
                     max_concurrency: int = 5,
                     usage_metadata: bool = False) -> list[AIResponse]:
        llm = self._get_cached_model(model_name, temperature, model_provider)
        results = llm.batch(prompts, config={"max_concurrency": max_concurrency})
        return [self._build_response(r, usage_metadata) for r in results]

    async def abatch_invoke(self, prompts: list[str],
                            model_name: str = settings.BASE_MODEL,
                            temperature: float = settings.BASE_TEMPERATURE,
                            model_provider: str = settings.BASE_MODEL_PROVIDER,
                            max_concurrency: int = 5,
                            usage_metadata: bool = False) -> list[AIResponse]:
        llm = self._get_cached_model(model_name, temperature, model_provider)
        results = await llm.abatch(prompts, config={"max_concurrency": max_concurrency})
        return [self._build_response(r, usage_metadata) for r in results]

    # -------------------------------------------------------------------------
    # Embeddings
    # -------------------------------------------------------------------------

    def embed(self, texts: list[str]) -> list[list[float]]:
        if AIService._embedder is None:
            AIService._embedder = GoogleGenerativeAIEmbeddings(
                model="models/embedding-001",
                google_api_key=settings.GEMINI_API_KEY,
            )
        return AIService._embedder.embed_documents(texts)
