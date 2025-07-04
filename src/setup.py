from setuptools import setup, find_packages
from pathlib import Path

# Read version from package
version_file = Path(__file__).parent / "ai_cookbook" / "__init__.py"
version_line = next(line for line in version_file.read_text().splitlines() if line.startswith("__version__"))
version = version_line.split("=")[1].strip().strip('"\'')

# Read README
readme_file = Path(__file__).parent.parent / "README.md"
long_description = readme_file.read_text() if readme_file.exists() else ""

setup(
    name="ai-cookbook",
    version=version,
    author="ethPandaOps",
    author_email="ethpandaops@ethereum.org",
    description="Unified installation system for ethPandaOps AI cookbook",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/ethpandaops/ai-cookbook",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Tools",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    python_requires=">=3.8",
    install_requires=[
        # No external dependencies - uses only Python standard library
    ],
    entry_points={
        "console_scripts": [
            "ai-cookbook=ai_cookbook.main:main",
        ],
    },
    include_package_data=True,
    package_data={
        "ai_cookbook": ["config/*"],
    },
)