"""Azure AI Foundry gpt-5.2 接続テスト (azure-ai-inference SDK)"""

from azure.ai.inference import ChatCompletionsClient
from azure.ai.inference.models import SystemMessage, UserMessage
from azure.core.credentials import AzureKeyCredential

ENDPOINT = "https://aoai-jaia-demo2.openai.azure.com/"
API_KEY = "70ogFGysFkPmDDJfsAspiTo82YXiR8EeO9l1R8IEB7zYjIFC1qlgJQQJ99CBACHYHv6XJ3w3AAABACOGTR0s"
DEPLOYMENT = "gpt-52-deployment"

print(f"Endpoint: {ENDPOINT}")
print(f"Deployment: {DEPLOYMENT}")

client = ChatCompletionsClient(
    endpoint=ENDPOINT,
    credential=AzureKeyCredential(API_KEY),
)

print("Sending request...")
response = client.complete(
    model=DEPLOYMENT,
    messages=[
        SystemMessage(content="あなたは監査AIアシスタントです。"),
        UserMessage(content="仕訳の異常検知について一文で説明してください。"),
    ],
    max_tokens=100,
)

print(f"Response: {response.choices[0].message.content}")
print(f"Model: {response.model}")
print(f"Tokens: input={response.usage.prompt_tokens}, output={response.usage.completion_tokens}")
print("\n=== SUCCESS ===")
