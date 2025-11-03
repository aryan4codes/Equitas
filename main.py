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


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Equitas - AI Safety Platform")
    parser.add_argument(
        "command",
        choices=["backend", "examples", "help"],
        nargs="?",
        default="help",
        help="Command to run"
    )
    
    args = parser.parse_args()
    
    if args.command == "backend":
        run_backend()
    elif args.command == "examples":
        run_examples()
    else:
        print("Equitas - AI Safety & Observability Platform")
        print("\nUsage:")
        print("  python main.py backend   - Start backend API")
        print("  python main.py examples  - Run SDK examples")
        print("\nFor more information, see README.md")


if __name__ == "__main__":
    main()
