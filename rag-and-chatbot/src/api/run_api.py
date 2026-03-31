#!/usr/bin/env python3
"""
Launcher script for SmartPark Admin API Server

Usage:
    python run_api.py [--port PORT] [--host HOST]

Examples:
    python run_api.py                    # Default: localhost:8000
    python run_api.py --port 8080        # Custom port
    python run_api.py --host 0.0.0.0     # Expose to network
"""

import argparse
import os
import sys
import uvicorn

# Add the src directory to Python path so uvicorn can find the api module
src_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)


def main():
    """Parse arguments and start the API server"""
    parser = argparse.ArgumentParser(
        description="SmartPark Admin API Server",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_api.py                    # Start on localhost:8000
  python run_api.py --port 8080        # Start on custom port
  python run_api.py --host 0.0.0.0     # Expose to network
        """
    )

    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Host to bind the server to (default: 0.0.0.0)"
    )

    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to bind the server to (default: 8000)"
    )

    parser.add_argument(
        "--reload",
        action="store_true",
        help="Enable auto-reload for development"
    )

    args = parser.parse_args()

    print("=" * 70)
    print("SmartPark Admin API Server")
    print("=" * 70)
    print(f"Server URL: http://{args.host}:{args.port}")
    print(f"API Documentation: http://{args.host}:{args.port}/docs")
    print(f"OpenAPI Schema: http://{args.host}:{args.port}/openapi.json")
    print("=" * 70)
    print("\nEndpoints:")
    print("  GET  /health                         - Health check")
    print("  GET  /reservations/pending           - List pending reservations")
    print("  POST /reservations/{id}/approve      - Approve a reservation")
    print("  POST /reservations/{id}/reject       - Reject a reservation")
    print("  GET  /reservations/{id}              - Get reservation details")
    print("\nPress CTRL+C to stop the server")
    print("=" * 70)
    print()

    uvicorn.run(
        "api.admin_api:app",
        host=args.host,
        port=args.port,
        reload=args.reload
    )


if __name__ == "__main__":
    main()
