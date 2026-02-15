"""Azure AI Foundry gpt-5.2 接続テスト (azure-ai-inference SDK)

環境変数から認証情報を読み込みます。
backend/.env が設定されていれば dotenv 経由でも読み込み可能です。
"""

import os
import sys

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

from azure.ai.inference import ChatCompletionsClient
from azure.ai.inference.models import SystemMessage, UserMessage
from azure.core.credentials import AzureKeyCredential

ENDPOINT = os.environ.get("AZURE_FOUNDRY_ENDPOINT", "")
API_KEY = os.environ.get("AZURE_FOUNDRY_API_KEY", "")
DEPLOYMENT = os.environ.get("AZURE_FOUNDRY_DEPLOYMENT", "gpt-52-deployment")

if not ENDPOINT or not API_KEY:
    print("ERROR: AZURE_FOUNDRY_ENDPOINT and AZURE_FOUNDRY_API_KEY must be set.")
    print("Set environment variables or configure backend/.env")
    sys.exit(1)

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
print(
    f"Tokens: input={response.usage.prompt_tokens}, output={response.usage.completion_tokens}"
)
print("\n=== SUCCESS ===")
