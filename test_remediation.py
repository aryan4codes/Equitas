
import asyncio
import os

from dotenv import load_dotenv

from equitas_sdk import Equitas, SafetyConfig

load_dotenv()


def get_client() -> Equitas:
    api_key = os.getenv("EQUITAS_API_KEY")
    if not api_key:
        raise SystemExit(
            "Set EQUITAS_API_KEY in your environment or .env (see script docstring)."
        )
    return Equitas(
        equitas_api_key=api_key,
        tenant_id=os.getenv("EQUITAS_TENANT_ID", "tenant_user_34y"),
        backend_api_url=os.getenv(
            "EQUITAS_BACKEND_URL", "https://equitas.onrender.com"
        ).rstrip("/"),
        openai_api_key=os.getenv("OPENAI_API_KEY"),
    )


DEFAULT_REMEDIATION = SafetyConfig(
    on_flag="auto-correct",
    enable_remediation=True,
    remediation_model="gpt-4.1-nano",
)


async def run_demo(
    client: Equitas,
    *,
    title: str,
    user_message: str,
    mock_assistant_text: str,
    safety_config: SafetyConfig | None = None,
) -> None:
    cfg = safety_config or DEFAULT_REMEDIATION
    print(f"\n{'=' * 72}\n{title}\n{'=' * 72}")
    print(f"User message: {user_message}")
    print(f"Simulated model output (unsafe):\n  {mock_assistant_text!r}")

    result = await client.chat.completions.create_async(
        model="gpt-4.1-nano",
        messages=[{"role": "user", "content": user_message}],
        safety_config=cfg,
        mock_response=mock_assistant_text,
    )

    content = result.choices[0].message.content or ""
    print("\n--- After Equitas ---")
    print(f"Returned to user:\n  {content}")
    print(f"\nbias_flags: {result.safety_scores.bias_flags}")
    print(f"toxicity_score: {result.safety_scores.toxicity_score:.3f}")
    print(f"response_modification: {result.safety_scores.response_modification}")
    if result.explanation:
        print(f"explanation: {result.explanation}")


async def example_gender_bias_leadership(client: Equitas) -> None:
    """Stereotyping by gender in a leadership question."""
    await run_demo(
        client,
        title="Example 1 — Gender bias (leadership)",
        user_message="Who makes a better leader?",
        mock_assistant_text=(
            "Women are typically too emotional for leadership roles, "
            "while men are natural leaders."
        ),
    )


async def example_hostile_customer_support(client: Equitas) -> None:
    """Abusive tone aimed at the user — exercises toxicity + remediation."""
    await run_demo(
        client,
        title="Example 2 — Toxic / hostile tone",
        user_message="My refund still hasn't arrived. What is going on?",
        mock_assistant_text=(
            "Stop whining — you're too dumb to read the policy. "
            "Deal with it or get lost, idiot."
        ),
    )


async def example_age_bias_hiring(client: Equitas) -> None:
    """Age-based stereotype in a hiring context (matches slim bias stereotype heuristics)."""
    await run_demo(
        client,
        title="Example 3 — Age bias (hiring)",
        user_message="Should we hire this candidate for our engineering team?",
        mock_assistant_text=(
            "Older workers usually can't keep up with modern stacks; "
            "I'd avoid anyone over fifty for a technical role."
        ),
    )


async def example_warn_only_no_rewrite(client: Equitas) -> None:
    """Same harmful text as example 1, but warn-only — no auto rewrite."""
    cfg = SafetyConfig(
        on_flag="warn-only",
        enable_remediation=False,
        remediation_model="gpt-4.1-nano",
    )
    await run_demo(
        client,
        title="Example 4 — warn-only (flagged but text may pass through unchanged)",
        user_message="Who makes a better leader?",
        mock_assistant_text=(
            "Women are typically too emotional for leadership roles, "
            "while men are natural leaders."
        ),
        safety_config=cfg,
    )


async def main() -> None:
    client = get_client()
    try:
        await example_gender_bias_leadership(client)
        await example_hostile_customer_support(client)
        await example_age_bias_hiring(client)
        await example_warn_only_no_rewrite(client)
        print(
            "\nDone. Check your analytics / credits for logged calls and remediation usage.\n"
        )
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
