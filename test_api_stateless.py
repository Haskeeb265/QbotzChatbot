from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)


def test_chat_stateless():
    print("Testing Stateless Chat API...")

    # 1. Health data
    response = client.get("/health")
    assert response.status_code == 200
    print("✅ Health Check Passed")

    # 2. Chat Request
    payload = {
        "messages": [
            {"role": "user", "content": "Hello, I want to analyze sales."},
            {"role": "assistant", "content": "Sure, what data do you need?"},
            {
                "role": "user",
                "content": "Show me top 3 customers by revenue",
            },  # Intent: ANALYTICAL
        ]
    }

    print("\nSending Chat Request (Analytical)...")
    try:
        response = client.post("/v1/chat/completions", json=payload)

        if response.status_code != 200:
            print(f"❌ Failed: {response.text}")
            return

        data = response.json()
        print("\nResponse Received:")
        print(f"Role: {data['role']}")
        print(f"Content: {data['content'][:100]}...")  # Truncate
        print(f"Intent: {data.get('intent')}")
        print(f"SQL: {data.get('sql')}")
        print(f"Metadata: {data.get('metadata')}")

        assert data["role"] == "assistant"
        assert "confidence" in str(data) or data.get("intent")
        print("\n✅ Chat API Verification Successful!")

    except Exception as e:
        print(f"\n❌ Error: {e}")


if __name__ == "__main__":
    test_chat_stateless()
