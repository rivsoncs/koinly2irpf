from setuptools import setup, find_packages

try:
    with open("README.md", "r", encoding="utf-8") as fh:
        long_description = fh.read()
except:
    long_description = "Conversor de relatórios Koinly para IRPF brasileiro"

setup(
    name="koinly2irpf",
    version="0.1.0",
    author="RIVSON DE CASTRO E SOUZA",
    author_email="",
    description="Conversor de relatórios Koinly para IRPF brasileiro",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/rivsoncs/koinly2irpf",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.8",
    install_requires=[
        "pdfplumber",
        "pandas",
        "pathlib",
        "python-dotenv",
    ],
    entry_points={
        "console_scripts": [
            "koinly2irpf=koinly2irpf.main_cli:main",
        ],
    },
)
