import setuptools

try:
    import fifoio
except ModuleNotFoundError:
    import sys
    import os

    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))
    import fifoio

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setuptools.setup(
    name="fifoio",
    version=fifoio.__version__,
    author=fifoio.__author__,
    author_email=fifoio.__email__,
    description=fifoio.__doc__,
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/LaughInJar/fifoio",
    project_urls={
        "Bug Tracker": "https://github.com/LaughInJar/fifoio/issues",
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    package_dir={"": "src"},
    packages=setuptools.find_packages(where="src"),
    python_requires=">=3.6",
)
