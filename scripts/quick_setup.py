#!/usr/bin/env python3
"""
JAIA Quick Setup Script

Interactive setup wizard for configuring JAIA development environment.
Supports both Japanese and English prompts.
"""

import os
import sys
import subprocess
from pathlib import Path


# Colors for terminal output
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    END = '\033[0m'
    BOLD = '\033[1m'


def print_header(text: str) -> None:
    """Print a styled header."""
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'=' * 60}{Colors.END}")
    print(f"{Colors.HEADER}{Colors.BOLD}  {text}{Colors.END}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'=' * 60}{Colors.END}\n")


def print_step(step: int, total: int, text: str) -> None:
    """Print a step indicator."""
    print(f"{Colors.CYAN}[{step}/{total}]{Colors.END} {text}")


def print_success(text: str) -> None:
    """Print a success message."""
    print(f"{Colors.GREEN}✓ {text}{Colors.END}")


def print_warning(text: str) -> None:
    """Print a warning message."""
    print(f"{Colors.WARNING}⚠ {text}{Colors.END}")


def print_error(text: str) -> None:
    """Print an error message."""
    print(f"{Colors.FAIL}✗ {text}{Colors.END}")


def ask_choice(prompt: str, options: list[str], default: int = 0) -> int:
    """Ask user to choose from options."""
    print(f"\n{prompt}")
    for i, option in enumerate(options):
        marker = ">" if i == default else " "
        print(f"  {marker} [{i + 1}] {option}")

    while True:
        try:
            choice = input(f"\n選択してください (1-{len(options)}) [{default + 1}]: ").strip()
            if not choice:
                return default
            idx = int(choice) - 1
            if 0 <= idx < len(options):
                return idx
        except ValueError:
            pass
        print_warning("無効な選択です。もう一度入力してください。")


def ask_input(prompt: str, default: str = "", secret: bool = False) -> str:
    """Ask user for text input."""
    if default:
        display = f"{prompt} [{default}]: "
    else:
        display = f"{prompt}: "

    if secret:
        import getpass
        value = getpass.getpass(display)
    else:
        value = input(display).strip()

    return value if value else default


def ask_yes_no(prompt: str, default: bool = True) -> bool:
    """Ask user a yes/no question."""
    default_str = "Y/n" if default else "y/N"
    while True:
        answer = input(f"{prompt} [{default_str}]: ").strip().lower()
        if not answer:
            return default
        if answer in ("y", "yes", "はい"):
            return True
        if answer in ("n", "no", "いいえ"):
            return False
        print_warning("y または n で回答してください。")


def check_python() -> bool:
    """Check Python version."""
    version = sys.version_info
    if version.major == 3 and version.minor >= 11:
        print_success(f"Python {version.major}.{version.minor}.{version.micro} ✓")
        return True
    else:
        print_error(f"Python 3.11以上が必要です (現在: {version.major}.{version.minor})")
        return False


def check_node() -> bool:
    """Check Node.js installation."""
    try:
        result = subprocess.run(
            ["node", "--version"],
            capture_output=True,
            text=True
        )
        version = result.stdout.strip()
        major = int(version.lstrip("v").split(".")[0])
        if major >= 18:
            print_success(f"Node.js {version} ✓")
            return True
        else:
            print_error(f"Node.js 18以上が必要です (現在: {version})")
            return False
    except FileNotFoundError:
        print_error("Node.js がインストールされていません")
        return False


def setup_backend(project_root: Path) -> bool:
    """Set up backend environment."""
    backend_dir = project_root / "backend"
    venv_dir = backend_dir / "venv"

    # Create virtual environment
    if not venv_dir.exists():
        print("仮想環境を作成中...")
        subprocess.run([sys.executable, "-m", "venv", str(venv_dir)])
        print_success("仮想環境を作成しました")
    else:
        print_success("仮想環境は既に存在します")

    # Install dependencies
    print("依存関係をインストール中...")
    if sys.platform == "win32":
        pip_path = venv_dir / "Scripts" / "pip.exe"
    else:
        pip_path = venv_dir / "bin" / "pip"

    result = subprocess.run(
        [str(pip_path), "install", "-r", str(backend_dir / "requirements.txt")],
        capture_output=True,
        text=True
    )

    if result.returncode == 0:
        print_success("バックエンドの依存関係をインストールしました")
        return True
    else:
        print_error("依存関係のインストールに失敗しました")
        print(result.stderr)
        return False


def setup_frontend(project_root: Path) -> bool:
    """Set up frontend environment."""
    frontend_dir = project_root / "frontend"

    print("フロントエンドの依存関係をインストール中...")
    result = subprocess.run(
        ["npm", "install"],
        cwd=str(frontend_dir),
        capture_output=True,
        text=True,
        shell=True
    )

    if result.returncode == 0:
        print_success("フロントエンドの依存関係をインストールしました")
        return True
    else:
        print_error("npm install に失敗しました")
        print(result.stderr)
        return False


def configure_llm(project_root: Path) -> None:
    """Configure LLM provider."""
    print_header("LLMプロバイダー設定")

    providers = [
        "Anthropic Claude (推奨)",
        "AWS Bedrock",
        "Google Vertex AI",
        "Azure OpenAI",
        "スキップ（後で設定）"
    ]

    choice = ask_choice("使用するLLMプロバイダーを選択してください:", providers)

    env_content = {
        "LLM_PROVIDER": "",
        "ANTHROPIC_API_KEY": "",
        "AWS_REGION": "us-east-1",
        "GCP_PROJECT_ID": "",
        "AZURE_OPENAI_ENDPOINT": "",
        "AZURE_OPENAI_API_KEY": "",
    }

    if choice == 0:  # Anthropic
        env_content["LLM_PROVIDER"] = "anthropic"
        api_key = ask_input("Anthropic APIキーを入力", secret=True)
        if api_key:
            env_content["ANTHROPIC_API_KEY"] = api_key

    elif choice == 1:  # AWS Bedrock
        env_content["LLM_PROVIDER"] = "bedrock"
        region = ask_input("AWSリージョン", default="us-east-1")
        env_content["AWS_REGION"] = region
        print("\n注意: AWS認証にはAWS CLIの設定が必要です")
        print("  aws configure を実行してください")

    elif choice == 2:  # Vertex AI
        env_content["LLM_PROVIDER"] = "vertex"
        project_id = ask_input("GCPプロジェクトID")
        if project_id:
            env_content["GCP_PROJECT_ID"] = project_id
        print("\n注意: GOOGLE_APPLICATION_CREDENTIALS 環境変数の設定が必要です")

    elif choice == 3:  # Azure OpenAI
        env_content["LLM_PROVIDER"] = "azure"
        endpoint = ask_input("Azure OpenAI エンドポイント")
        api_key = ask_input("Azure OpenAI APIキー", secret=True)
        if endpoint:
            env_content["AZURE_OPENAI_ENDPOINT"] = endpoint
        if api_key:
            env_content["AZURE_OPENAI_API_KEY"] = api_key

    else:  # Skip
        env_content["LLM_PROVIDER"] = "anthropic"
        print_warning("LLM設定をスキップしました。後で backend/.env を編集してください。")
        return

    # Write .env file
    env_path = project_root / "backend" / ".env"
    env_lines = [
        "# JAIA Backend Configuration",
        "# Generated by quick_setup.py",
        "",
        "# Application",
        "APP_NAME=JAIA",
        "DEBUG=true",
        "ENVIRONMENT=development",
        "",
        "# Server",
        "HOST=127.0.0.1",
        "PORT=8090",
        "",
        "# Database",
        "DATA_DIR=./data",
        "DUCKDB_PATH=./data/jaia.duckdb",
        "SQLITE_PATH=./data/jaia_meta.db",
        "",
        "# LLM Provider",
        f"LLM_PROVIDER={env_content['LLM_PROVIDER']}",
        "",
    ]

    if env_content["ANTHROPIC_API_KEY"]:
        env_lines.append(f"ANTHROPIC_API_KEY={env_content['ANTHROPIC_API_KEY']}")
    if env_content["AWS_REGION"]:
        env_lines.append(f"AWS_REGION={env_content['AWS_REGION']}")
    if env_content["GCP_PROJECT_ID"]:
        env_lines.append(f"GCP_PROJECT_ID={env_content['GCP_PROJECT_ID']}")
    if env_content["AZURE_OPENAI_ENDPOINT"]:
        env_lines.append(f"AZURE_OPENAI_ENDPOINT={env_content['AZURE_OPENAI_ENDPOINT']}")
    if env_content["AZURE_OPENAI_API_KEY"]:
        env_lines.append(f"AZURE_OPENAI_API_KEY={env_content['AZURE_OPENAI_API_KEY']}")

    env_lines.extend([
        "",
        "# Performance",
        "BATCH_SIZE=10000",
        "MAX_WORKERS=4",
        "CACHE_TTL_SECONDS=300",
        "",
        "# Logging",
        "LOG_LEVEL=INFO",
    ])

    with open(env_path, "w", encoding="utf-8") as f:
        f.write("\n".join(env_lines))

    print_success(f".env ファイルを作成しました: {env_path}")


def configure_frontend(project_root: Path) -> None:
    """Configure frontend environment."""
    env_path = project_root / "frontend" / ".env.local"

    env_content = """# JAIA Frontend Configuration
# Generated by quick_setup.py

# API
VITE_API_BASE=http://localhost:8090/api/v1

# Development
NODE_ENV=development
"""

    with open(env_path, "w", encoding="utf-8") as f:
        f.write(env_content)

    print_success(f"フロントエンド設定を作成しました: {env_path}")


def main():
    """Main setup wizard."""
    print_header("JAIA クイックセットアップ")
    print("Journal entry AI Analyzer のセットアップを開始します。\n")

    # Determine project root
    script_dir = Path(__file__).parent
    project_root = script_dir.parent

    print(f"プロジェクトディレクトリ: {project_root}\n")

    # Step 1: Check requirements
    print_step(1, 5, "システム要件を確認中...")
    python_ok = check_python()
    node_ok = check_node()

    if not python_ok or not node_ok:
        print_error("\nシステム要件を満たしていません。不足しているソフトウェアをインストールしてください。")
        sys.exit(1)

    # Step 2: Setup backend
    print_step(2, 5, "バックエンドをセットアップ中...")
    if not setup_backend(project_root):
        print_error("\nバックエンドのセットアップに失敗しました。")
        sys.exit(1)

    # Step 3: Setup frontend
    print_step(3, 5, "フロントエンドをセットアップ中...")
    if not setup_frontend(project_root):
        print_error("\nフロントエンドのセットアップに失敗しました。")
        sys.exit(1)

    # Step 4: Configure LLM
    print_step(4, 5, "LLMプロバイダーを設定中...")
    configure_llm(project_root)

    # Step 5: Configure frontend
    print_step(5, 5, "フロントエンド設定を作成中...")
    configure_frontend(project_root)

    # Create data directory
    data_dir = project_root / "backend" / "data"
    data_dir.mkdir(exist_ok=True)

    # Summary
    print_header("セットアップ完了")

    print("次のステップ:")
    print(f"{Colors.CYAN}1.{Colors.END} サンプルデータをロード:")
    print(f"   cd backend && .\\venv\\Scripts\\activate")
    print(f"   python ..\\scripts\\load_sample_data.py")
    print()
    print(f"{Colors.CYAN}2.{Colors.END} バックエンドを起動:")
    print(f"   python -m uvicorn app.main:app --host 127.0.0.1 --port 8090")
    print()
    print(f"{Colors.CYAN}3.{Colors.END} フロントエンドを起動（別ターミナル）:")
    print(f"   cd frontend && npm run dev")
    print()
    print(f"{Colors.CYAN}4.{Colors.END} ブラウザでアクセス:")
    print(f"   http://localhost:5290")
    print()
    print(f"{Colors.GREEN}Happy auditing! 🎉{Colors.END}\n")


if __name__ == "__main__":
    main()
