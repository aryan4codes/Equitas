"""
Equitas - AI Safety & Observability Platform

Entry point for running the backend API or SDK examples.
"""

import sys
import argparse


def run_backend():
    """Run the Equitas backend API server."""
    import uvicorn
    from backend_api.main import app
    
    print("Starting Equitas Backend API...")
    print("API will be available at http://localhost:8000")
    print("API docs at http://localhost:8000/docs")
    print("\nPress CTRL+C to stop\n")
    
    uvicorn.run(
        "backend_api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )


def run_examples():
    """Run SDK examples."""
    import asyncio
    import sys
    import os
    
    # Add examples to path
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "examples"))
    
    from basic_usage import main as basic_main
    
    print("Running Equitas SDK Examples...")
    print("=" * 60)
    asyncio.run(basic_main())


def run_tests():
    """Run SHAP/LIME/Detoxify tests."""
    import asyncio
    import sys
    from pathlib import Path
    
    # Import test script
    test_file = Path(__file__).parent / "test_shap_lime.py"
    if test_file.exists():
        print("Running Equitas SHAP/LIME/Detoxify Tests...")
        print("=" * 60)
        exec(open(test_file).read())
    else:
        print("Test file not found. Run: python test_shap_lime.py")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Equitas - AI Safety Platform")
    parser.add_argument(
        "command",
        choices=["backend", "examples", "test", "help"],
        nargs="?",
        default="help",
        help="Command to run"
    )
    
    args = parser.parse_args()
    
    if args.command == "backend":
        run_backend()
    elif args.command == "examples":
        run_examples()
    elif args.command == "test":
        run_tests()
    else:
        print("Equitas - AI Safety & Observability Platform")
        print("\nUsage:")
        print("  python main.py backend   - Start backend API")
        print("  python main.py examples  - Run SDK examples")
        print("  python main.py test      - Run SHAP/LIME/Detoxify tests")
        print("\nFor more information, see README.md")


if __name__ == "__main__":
    main()
