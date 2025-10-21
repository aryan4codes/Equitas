"""
equitas - AI Safety & Observability Platform

Entry point for running the Guardian backend or SDK examples.
"""

import sys
import argparse


def run_guardian():
    """Run the Guardian backend server."""
    import uvicorn
    from guardian.main import app
    
    print(" Starting equitas Guardian Backend...")
    print(" API will be available at http://localhost:8000")
    print(" API docs at http://localhost:8000/docs")
    print("\nPress CTRL+C to stop\n")
    
    uvicorn.run(
        "guardian.main:app",
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
    
    print("🎯 Running equitas SDK Examples...")
    print("=" * 60)
    asyncio.run(basic_main())


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="equitas - AI Safety Platform")
    parser.add_argument(
        "command",
        choices=["guardian", "examples", "help"],
        nargs="?",
        default="help",
        help="Command to run"
    )
    
    args = parser.parse_args()
    
    if args.command == "guardian":
        run_guardian()
    elif args.command == "examples":
        run_examples()
    else:
        print("equitas - AI Safety & Observability Platform")
        print("\nUsage:")
        print("  python main.py guardian   - Start Guardian backend")
        print("  python main.py examples   - Run SDK examples")
        print("\nFor more information, see README.md")


if __name__ == "__main__":
    main()
