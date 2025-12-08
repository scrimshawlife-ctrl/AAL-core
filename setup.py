#!/usr/bin/env python3
"""Setup file for AAL-Core ABX-Runes Memory Governance Layer."""

from setuptools import setup, find_packages

setup(
    name="aal-core",
    version="0.1.0",
    description="AAL-Core engine with ABX-Runes memory governance layer",
    author="Tachyon Team",
    packages=find_packages(),
    python_requires=">=3.7",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
)
