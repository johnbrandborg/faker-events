#!/usr/bin/env python

from setuptools import find_packages, setup

EXCLUDED_PACKAGES = [
   'docs',
   'tests',
   'tests.*'
]

INSTALL_REQUIRES = [
    'faker>=5.0,<5.1',
]

KAFKA_REQUIRES = [
    'kafka-python>=2.0,<2.1',
]

KINESIS_REQUIRES = [
    'boto3>=1.16,<1.17',
]

TEST_REQUIRES = [
    'flake8',
    'pytest',
    'pytest-cov'
]

with open('README.md') as readme_file:
    LONG_DESCRIPTION = readme_file.read()

with open('VERSION') as version_file:
    VERSION = version_file.read().strip()

setup(name='Faker-Events',
      version=VERSION,
      description='Generates Events with Fake data.',
      long_description=LONG_DESCRIPTION,
      long_description_content_type='text/markdown',
      classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3 :: Only',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: Software Development :: Testing',
        'Topic :: Utilities',
      ],
      keywords='faker events stream data test mock generator',
      author='johnbrandborg',
      author_email='john.brandborg@protonmail.com',
      url='https://github.com/johnbrandborg/faker-events',
      license='MIT License',
      packages=find_packages(exclude=EXCLUDED_PACKAGES),
      python_requires='>=3.6',
      install_requires=INSTALL_REQUIRES,
      extras_require={
        'dev': TEST_REQUIRES + KAFKA_REQUIRES + KINESIS_REQUIRES,
        'kafka': KAFKA_REQUIRES,
        'kinesis': KINESIS_REQUIRES
      })
