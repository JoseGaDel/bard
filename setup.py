from setuptools import setup, find_packages

with open('requirements.txt') as f:
    required = f.read().splitlines()

setup(
    name="bard",
    version="1.0.0",
    packages=find_packages(exclude=["server", "examples"]),
    install_requires=required,
    author="Jose Gallego Delgado",
    author_email="jogadel137@gmail.com",
    description="A framework for biodiversity API retrieval and data processing",
    long_description=open('README.md').read(),
    long_description_content_type="text/markdown",
    url="https://github.com/JoseGaDel/bard",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.6',
)