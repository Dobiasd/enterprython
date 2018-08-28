import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="enterprython",
    version="0.1.0",
    author="Tobias Hermann",
    author_email="editgym@gmail.com",
    description="Type-based dependency-injection framework",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="http://github.com/Dobiasd/enterprython",
    packages=setuptools.find_packages(),
    classifiers=(
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ),
)