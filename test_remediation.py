import asyncio
from equitas_sdk import Equitas, SafetyConfig
from dotenv import load_dotenv
load_dotenv()
import os

async def main():
    # Initialize without an OpenAI key!
    client = Equitas(
        equitas_api_key="eq_EoeIc3A79z-pVAIwcjvG0qUgXK0olW4wJpKR4wo8aIk",
        tenant_id="tenant_user_34y",
        backend_api_url="https://equitas.onrender.com"
    )

    # Define the safety config, explicitly asking backend to use gpt-4.1-nano for rewrites
    config = SafetyConfig(
        enable_toxicity=False,
        enable_bias=True,
        enable_remediation=True,
        remediation_model="gpt-4.1-nano",
        on_flag="auto-correct",
        openai_api_key=os.getenv("OPENAI_API_KEY")
    )

    print("--- Simulating an LLM Output (No OpenAI Key Used!) ---")
    mock_llm_response = "Women are typically too emotional for leadership roles, while men are natural leaders."
    print(f"Original LLM Output: {mock_llm_response}")

    print("\n--- Running Equitas Interception & Auto-Remediation ---")
    
    # We pass the mock_response parameter to bypass actual LLM generation for testing
    final_output = await client.chat.completions.create_async(
        model="gpt-4.1-nano",
        messages=[{"role": "user", "content": "Who makes a better leader?"}],
        safety_config=config,
        mock_response=mock_llm_response,
    )

    print(f"\nFinal Output returned to user: {final_output.choices[0].message.content}")
    print("\nCheck your analytics dashboard for the original vs remediated response, and your credit history for the 2.0 credit deduction!")

if __name__ == "__main__":
    asyncio.run(main())
