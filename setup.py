import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="compare_it",
    version="0.0.5",
    author="ALIASGAR - ALI",
    author_email="aholo2000@gmail.com",
    description="comparision of two text configurations files or two excel facts files ",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/aliasgar1978/compare_it",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.9',
    install_requires=['pandas', 'nettoolkit',
        'compare-it',
    ]
)

