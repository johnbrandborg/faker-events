#!/usr/bin/env python

from pathlib import Path

from setuptools import find_packages, setup

here = Path(__file__).resolve().parent
README = (here / 'README.md').read_text(encoding='utf-8')
VERSION = (here / 'VERSION').read_text(encoding='utf-8').strip()

excluded_packages = ["docs", "tests", "tests.*"]

setup(
    name='Faker-Events',
    version=VERSION,
    description="Generates Events with Fake data.",
    long_description=README,
    classifiers=[
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: Software Development :: Testing',
        'Topic :: Utilities',
        'License :: OSI Approved :: MIT License',
    ],
    keywords='',
    author='johnbrandborg',
    author_email='john.brandborg@protonmail.com',
    url='https://github.com/johnbrandborg/faker-events',
    license='MIT License',
    packages=find_packages(exclude=excluded_packages),
    platforms=["any"],
    python_requires=">=3.6",
    install_requires=[
        "awscli>=1.18,<1.19",
        "faker>=5.0,<5.1",
        "kafka-python>=2.0,<2.1",
    ],
)
