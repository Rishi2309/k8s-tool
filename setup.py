"""
Setup script for the K8s automation tool.
This allows the tool to be installed using pip.
"""

from setuptools import setup, find_packages
import os

# Get the directory containing setup.py
setup_dir = os.path.dirname(os.path.abspath(__file__))

# Read README.md from the same directory as setup.py
with open(os.path.join(setup_dir, "README.md"), "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="k8s-tool",
    version="0.1.0",
    author="Rishi Kumar",
    author_email="rishivlr2309@gamil.com",
    description="Tool for automating Kubernetes operations with KEDA",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/Rishi2309/k8s-tool",
    packages=find_packages(include=["k8s_tool", "k8s_tool.*"]),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.7",
    install_requires=[
        "click>=8.0.0",
        "pyyaml>=5.1",
        "pytest>=7.0.0",
    ],
    entry_points={
        "console_scripts": [
            "k8s-tool=k8s_tool.cli.cli:main",
        ],
    },
)