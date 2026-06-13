"""
Offline STT Pipeline - Main Entry Point

Cross-platform offline Speech-to-Text API server for Voice AI integration.
Runs a local REST API that provides OpenAI-compatible transcription endpoints.
"""

import sys
import signal
import logging
import argparse
import webbrowser
from pathlib import Path

import uvicorn

from .api import create_app
from .utils.config import ConfigManager, get_app_data_dir


def setup_logging(verbose: bool = False):
    """Configure application logging."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    # Suppress noisy loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("multipart").setLevel(logging.WARNING)


def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        prog="offline-stt-pipeline",
        description="Offline Speech-to-Text API Pipeline for Voice AI",
    )
    parser.add_argument(
        "--host",
        type=str,
        default="0.0.0.0",
        help="Host to bind the server to (default: 0.0.0.0)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to run the server on (default: 8000)",
    )
    parser.add_argument(
        "--model",
        type=str,
        default=None,
        help="Model to load at startup (e.g., tiny, base, small, medium, large-v3)",
    )
    parser.add_argument(
        "--device",
        type=str,
        choices=["auto", "cpu", "cuda"],
        default="auto",
        help="Device to use for inference (default: auto)",
    )
    parser.add_argument(
        "--compute-type",
        type=str,
        choices=["auto", "int8", "float16", "float32"],
        default="auto",
        help="Compute type for inference (default: auto)",
    )
    parser.add_argument(
        "--models-dir",
        type=str,
        default=None,
        help="Directory to store/load models from",
    )
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="Don't open the web UI in browser on startup",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging",
    )
    return parser.parse_args()


def main():
    """Main entry point for the application."""
    args = parse_args()
    setup_logging(args.verbose)
    
    logger = logging.getLogger(__name__)
    
    # Update config with CLI args
    config = ConfigManager()
    
    if args.model:
        config.update_engine(model_size=args.model)
    if args.device:
        config.update_engine(device=args.device)
    if args.compute_type:
        config.update_engine(compute_type=args.compute_type)
    if args.models_dir:
        config.config.models_dir = args.models_dir
        config.save()
    
    config.update_server(host=args.host, port=args.port)

    # Print startup banner
    print(r"""
    ╔══════════════════════════════════════════════════════╗
    ║         Offline STT Pipeline v1.0.0                 ║
    ║   Cross-platform Speech-to-Text for Voice AI        ║
    ╚══════════════════════════════════════════════════════╝
    """)
    print(f"  Server:     http://{args.host}:{args.port}")
    print(f"  API Docs:   http://localhost:{args.port}/docs")
    print(f"  Web UI:     http://localhost:{args.port}/")
    print(f"  Models Dir: {config.config.models_dir}")
    print(f"  Device:     {args.device}")
    print()

    # Open browser
    if not args.no_browser:
        try:
            webbrowser.open(f"http://localhost:{args.port}")
        except Exception:
            pass

    # Handle graceful shutdown
    def signal_handler(sig, frame):
        logger.info("Shutting down...")
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Create and run the app
    app = create_app()
    
    uvicorn.run(
        app,
        host=args.host,
        port=args.port,
        log_level="info" if not args.verbose else "debug",
    )


if __name__ == "__main__":
    main()
