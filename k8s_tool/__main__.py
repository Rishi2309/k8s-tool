"""
Main entry point for the K8s automation tool.
This file allows running the tool as a module: python -m k8s_tool
"""

from .cli.cli import main

if __name__ == "__main__":
    main()