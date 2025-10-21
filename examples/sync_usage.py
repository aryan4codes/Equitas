"""
Example usage of equitas SDK in synchronous code.
For simple scripts that don't use async/await.
"""

from equitas_sdk import equitas, SafetyConfig


def main():
    # Initialize equitas client
    equitas = equitas(
        openai_api_key="sk-your-openai-api-key",
        equitas_api_key="fs-dev-key-123",
        tenant_id="tenant_demo",
        guardian_base_url="http://localhost:8000",
        user_id="user_001",
    )
    
    print("=" * 60)
    print("equitas SDK - Synchronous Example")
    print("=" * 60)
    
    # Example: Safe query with sync interface
    print("\nSafe Query Example:")
    print("-" * 60)
    
    try:
        response = equitas.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "user", "content": "What is the capital of France?"}
            ],
            safety_config=SafetyConfig(on_flag="warn-only")
        )
        
        print(f"Response: {response.choices[0].message.content}")
        print(f"Toxicity Score: {response.safety_scores.toxicity_score}")
        print(f"Latency: {response.latency_ms:.2f}ms")
    except RuntimeError as e:
        print(f"Error: {e}")
        print("\nNote: If you see an event loop error, use the async version instead.")
        print("See examples/basic_usage.py for async examples.")
    except Exception as e:
        print(f"Error: {e}")
    
    print("\n" + "=" * 60)
    print("Example completed!")
    print("=" * 60)


if __name__ == "__main__":
    main()
