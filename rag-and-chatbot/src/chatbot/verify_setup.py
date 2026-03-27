"""
Setup Verification Script
Checks if all required components are properly configured
"""

import os
import sys
from pathlib import Path


def check_api_key():
    """Check if OpenAI API key is configured"""
    from dotenv import load_dotenv
    load_dotenv()

    api_key = os.getenv("OPENAI_API_KEY")
    if api_key and api_key != "your-openai-api-key-here":
        print("✅ OpenAI API key found")
        return True
    else:
        print("❌ OpenAI API key not configured")
        print("   Please set OPENAI_API_KEY in .env file")
        return False


def check_databases():
    """Check if databases exist"""
    data_dir = Path(__file__).parent.parent.parent / "data"

    checks = []

    # Check Milvus database
    milvus_db = data_dir / "parking.db"
    if milvus_db.exists():
        print(f"✅ Milvus database found: {milvus_db}")
        checks.append(True)
    else:
        print(f"❌ Milvus database not found: {milvus_db}")
        print("   Run generate_data.ipynb to create it")
        checks.append(False)

    # Check SQLite database
    sqlite_db = data_dir / "parking_db.sqlite"
    if sqlite_db.exists():
        print(f"✅ SQLite database found: {sqlite_db}")
        checks.append(True)
    else:
        print(f"❌ SQLite database not found: {sqlite_db}")
        print("   Run generate_data.ipynb to create it")
        checks.append(False)

    return all(checks)


def check_dependencies():
    """Check if required packages are installed"""
    required_packages = [
        "langchain",
        "langgraph",
        "langchain_openai",
        "langchain_milvus",
        "langchain_huggingface",
        "sentence_transformers",
        "openai"
    ]

    all_installed = True

    for package in required_packages:
        try:
            __import__(package)
            print(f"✅ {package} installed")
        except ImportError:
            print(f"❌ {package} NOT installed")
            all_installed = False

    if not all_installed:
        print("\n   Install missing packages with:")
        print("   uv sync")
        print("   or: pip install -e .")

    return all_installed


def check_models():
    """Check if HuggingFace models are accessible"""
    try:
        print("\nChecking HuggingFace models...")
        from langchain_huggingface import HuggingFaceEmbeddings
        from langchain_community.cross_encoders import HuggingFaceCrossEncoder

        # This will download models if not cached
        print("  Loading embedding model...")
        embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2"
        )
        print("✅ Embedding model loaded")

        print("  Loading reranker model...")
        reranker = HuggingFaceCrossEncoder(model_name="BAAI/bge-reranker-base")
        print("✅ Reranker model loaded")

        return True
    except Exception as e:
        print(f"❌ Error loading models: {e}")
        return False


def main():
    """Run all verification checks"""
    print("="*60)
    print("🔍 Parking Chatbot Setup Verification")
    print("="*60)
    print()

    print("[1/4] Checking dependencies...")
    deps_ok = check_dependencies()
    print()

    print("[2/4] Checking API key...")
    api_ok = check_api_key()
    print()

    print("[3/4] Checking databases...")
    db_ok = check_databases()
    print()

    print("[4/4] Checking AI models...")
    models_ok = check_models()
    print()

    print("="*60)
    if all([deps_ok, api_ok, db_ok, models_ok]):
        print("✅ All checks passed! You're ready to use the chatbot.")
        print("\nTo start the chatbot:")
        print("  python -m rag_and_chatbot.src.chatbot.main")
    else:
        print("❌ Some checks failed. Please fix the issues above.")
        sys.exit(1)
    print("="*60)


if __name__ == "__main__":
    main()
