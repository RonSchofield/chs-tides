import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="chstides",
    version="0.3.2",
    author="Ron Schofield",
    author_email="ronschofield@eastlink.ca",
    description="Python Wrapper for Canadian Hydrographic Service (CHS) Integrated Water Level System API",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/RonSchofield/chs-tides",
    packages=setuptools.find_packages(),
    install_requires=[
        "aiohttp",
        "geopy",
        "voluptuous",
    ],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.6',
)