import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="enterprython",
    version="0.7.0",
    author="Tobias Hermann",
    author_email="editgym@gmail.com",
    description="Type-based dependency injection",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="http://github.com/Dobiasd/enterprython",
    package_data={"enterprython": ["py.typed"]},
    packages=["enterprython"],
    python_requires=">=3.7",
    classifiers=(
        "Programming Language :: Python :: 3.7",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ),
)
