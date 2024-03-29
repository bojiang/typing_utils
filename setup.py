import setuptools

with open("README.md", "r", encoding="utf8") as f:
    long_description = f.read()

setuptools.setup(
    name="typing_utils",
    version="0.1.0",
    author="bojiang",
    author_email="bojiang_@outlook.com",
    description="utils to inspect Python type annotations",
    long_description=long_description,
    license="Apache License 2.0",
    long_description_content_type="text/markdown",
    url="https://github.com/bojiang/typing_utils",
    packages=setuptools.find_packages(exclude=["tests*"]),
    classifiers=[
        "Operating System :: OS Independent",
        "Development Status :: 2 - Pre-Alpha",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: Implementation :: CPython",
    ],
    python_requires=">=3.6.1",
    extras_require={"test": ["pytest"]},
)
