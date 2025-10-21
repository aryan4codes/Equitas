"""
FairSight Client - Main SDK interface that wraps OpenAI API.
"""

import asyncio
import time
from typing import Any, Dict, List, Optional
import httpx
from openai import OpenAI
from openai.types.chat import ChatCompletion

from .models import SafeCompletionResponse, SafetyConfig, SafetyScores
from .exceptions import SafetyViolationException, RemediationFailedException


class FairSight:
    """
    FairSight SDK client that enhances OpenAI API calls with safety checks.
    
    Usage:
        fairsight = FairSight(
            openai_api_key="sk-...",
            fairsight_api_key="fs-...",
            tenant_id="org123"
        )
        
        response = fairsight.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": "Hello!"}],
            safety_config=SafetyConfig(on_flag="auto-correct")
        )
    """

    def __init__(
        self,
        openai_api_key: str,
        fairsight_api_key: str,
        tenant_id: str,
        guardian_base_url: str = "http://localhost:8000",
        user_id: Optional[str] = None,
    ):
        """
        Initialize FairSight client.
        
        Args:
            openai_api_key: OpenAI API key
            fairsight_api_key: FairSight Guardian API key
            tenant_id: Organization/tenant identifier
            guardian_base_url: URL of Guardian backend API
            user_id: Optional user identifier for logging
        """
        self.openai_client = OpenAI(api_key=openai_api_key)
        self.fairsight_api_key = fairsight_api_key
        self.tenant_id = tenant_id
        self.user_id = user_id or "default_user"
        self.guardian_base_url = guardian_base_url.rstrip("/")
        
        # Initialize HTTP client for Guardian API
        self.http_client = httpx.AsyncClient(
            headers={
                "Authorization": f"Bearer {fairsight_api_key}",
                "X-Tenant-ID": tenant_id,
            },
            timeout=30.0,
        )
        
        # ChatCompletion wrapper
        self.chat = ChatCompletionWrapper(self)

    def _get_headers(self) -> Dict[str, str]:
        """Get headers for Guardian API requests."""
        return {
            "Authorization": f"Bearer {self.fairsight_api_key}",
            "X-Tenant-ID": self.tenant_id,
        }

    async def _analyze_toxicity(self, text: str) -> Dict[str, Any]:
        """Analyze text for toxicity."""
        try:
            response = await self.http_client.post(
                f"{self.guardian_base_url}/v1/analysis/toxicity",
                json={"text": text, "tenant_id": self.tenant_id},
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Toxicity analysis failed: {e}")
            return {"toxicity_score": 0.0, "flagged": False, "categories": []}

    async def _analyze_bias(self, prompt: str, response_text: str) -> Dict[str, Any]:
        """Analyze for demographic bias."""
        try:
            response = await self.http_client.post(
                f"{self.guardian_base_url}/v1/analysis/bias",
                json={
                    "prompt": prompt,
                    "response": response_text,
                    "tenant_id": self.tenant_id,
                },
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Bias analysis failed: {e}")
            return {"bias_score": 0.0, "flags": []}

    async def _detect_jailbreak(self, text: str) -> Dict[str, Any]:
        """Detect jailbreak/prompt injection attempts."""
        try:
            response = await self.http_client.post(
                f"{self.guardian_base_url}/v1/analysis/jailbreak",
                json={"text": text, "tenant_id": self.tenant_id},
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Jailbreak detection failed: {e}")
            return {"jailbreak_flag": False}

    async def _get_explanation(self, text: str, issues: List[str]) -> Dict[str, Any]:
        """Get explanation for flagged content."""
        try:
            response = await self.http_client.post(
                f"{self.guardian_base_url}/v1/analysis/explain",
                json={"text": text, "issues": issues, "tenant_id": self.tenant_id},
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Explanation generation failed: {e}")
            return {"explanation": "Unable to generate explanation"}

    async def _remediate(self, text: str, issue: str) -> Dict[str, Any]:
        """Remediate unsafe content."""
        try:
            response = await self.http_client.post(
                f"{self.guardian_base_url}/v1/analysis/remediate",
                json={"text": text, "issue": issue, "tenant_id": self.tenant_id},
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Remediation failed: {e}")
            raise RemediationFailedException(f"Failed to remediate content: {e}")

    async def _log_call(self, log_data: Dict[str, Any]) -> None:
        """Asynchronously log API call to Guardian."""
        try:
            await self.http_client.post(
                f"{self.guardian_base_url}/v1/log",
                json=log_data,
            )
        except Exception as e:
            print(f"Logging failed: {e}")

    async def close(self):
        """Close HTTP client."""
        await self.http_client.aclose()


class ChatCompletionWrapper:
    """Wrapper for chat completions with safety checks."""

    def __init__(self, fairsight_client: FairSight):
        self.client = fairsight_client
        self.completions = CompletionsWrapper(fairsight_client)


class CompletionsWrapper:
    """Completions API wrapper."""

    def __init__(self, fairsight_client: FairSight):
        self.client = fairsight_client

    def create(
        self,
        model: str,
        messages: List[Dict[str, str]],
        safety_config: Optional[SafetyConfig] = None,
        **kwargs,
    ) -> SafeCompletionResponse:
        """
        Create a chat completion with safety checks.
        
        Args:
            model: Model name (e.g., "gpt-4")
            messages: List of message dicts
            safety_config: Safety configuration
            **kwargs: Additional OpenAI parameters
            
        Returns:
            SafeCompletionResponse with safety metadata
        """
        # Run async operations in sync context
        return asyncio.run(self._create_async(model, messages, safety_config, **kwargs))

    async def _create_async(
        self,
        model: str,
        messages: List[Dict[str, str]],
        safety_config: Optional[SafetyConfig] = None,
        **kwargs,
    ) -> SafeCompletionResponse:
        """Internal async implementation."""
        start_time = time.time()
        safety_config = safety_config or SafetyConfig()
        
        # Extract prompt text
        prompt_text = " ".join([msg.get("content", "") for msg in messages])
        
        # 1. Pre-check: Analyze prompt for jailbreak
        jailbreak_result = await self.client._detect_jailbreak(prompt_text)
        
        if jailbreak_result.get("jailbreak_flag") and safety_config.on_flag == "strict":
            raise SafetyViolationException("Jailbreak attempt detected in prompt")
        
        # 2. Call OpenAI API
        openai_start = time.time()
        completion: ChatCompletion = self.client.openai_client.chat.completions.create(
            model=model, messages=messages, **kwargs
        )
        openai_latency = (time.time() - openai_start) * 1000
        
        # Extract response text
        response_text = completion.choices[0].message.content or ""
        
        # 3. Post-check: Analyze response
        toxicity_task = self.client._analyze_toxicity(response_text)
        bias_task = self.client._analyze_bias(prompt_text, response_text)
        
        toxicity_result, bias_result = await asyncio.gather(toxicity_task, bias_task)
        
        # Build safety scores
        safety_scores = SafetyScores(
            toxicity_score=toxicity_result.get("toxicity_score", 0.0),
            toxicity_categories=toxicity_result.get("categories", []),
            bias_flags=bias_result.get("flags", []),
            jailbreak_flag=jailbreak_result.get("jailbreak_flag", False),
            response_modification="none",
        )
        
        # Determine if content is flagged
        is_flagged = (
            toxicity_result.get("flagged", False)
            or len(bias_result.get("flags", [])) > 0
            or jailbreak_result.get("jailbreak_flag", False)
        )
        
        final_response_text = response_text
        explanation = None
        
        # 4. Handle flagged content
        if is_flagged:
            issues = []
            if toxicity_result.get("flagged"):
                issues.append("toxicity")
            if bias_result.get("flags"):
                issues.append("bias")
            if jailbreak_result.get("jailbreak_flag"):
                issues.append("jailbreak")
            
            # Get explanation
            explanation_result = await self.client._get_explanation(response_text, issues)
            explanation = explanation_result.get("explanation")
            
            # Handle based on safety config
            if safety_config.on_flag == "strict":
                raise SafetyViolationException(
                    f"Safety violation detected: {explanation}"
                )
            elif safety_config.on_flag == "auto-correct":
                # Attempt remediation
                remediation_result = await self.client._remediate(
                    response_text, issues[0]
                )
                final_response_text = remediation_result.get("remediated_text", response_text)
                safety_scores.response_modification = "rephrased"
                
                # Update completion object
                completion.choices[0].message.content = final_response_text
        
        total_latency = (time.time() - start_time) * 1000
        fairsight_overhead = total_latency - openai_latency
        
        # 5. Log asynchronously (don't await)
        log_data = {
            "tenant_id": self.client.tenant_id,
            "user_id": self.client.user_id,
            "model": model,
            "prompt": prompt_text,
            "response": final_response_text,
            "original_response": response_text if is_flagged else None,
            "safety_scores": safety_scores.dict(),
            "latency_ms": total_latency,
            "fairsight_overhead_ms": fairsight_overhead,
            "tokens_input": completion.usage.prompt_tokens if completion.usage else 0,
            "tokens_output": completion.usage.completion_tokens if completion.usage else 0,
            "timestamp": time.time(),
            "flagged": is_flagged,
            "explanation": explanation,
        }
        
        # Fire and forget logging
        asyncio.create_task(self.client._log_call(log_data))
        
        # 6. Build and return response
        return SafeCompletionResponse(
            id=completion.id,
            object=completion.object,
            created=completion.created,
            model=completion.model,
            choices=completion.choices,
            usage=completion.usage,
            safety_scores=safety_scores,
            explanation=explanation,
            latency_ms=total_latency,
        )
