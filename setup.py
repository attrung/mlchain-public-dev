#!/usr/bin/env python
import os
from setuptools import setup, find_packages
__version__ = "0.0.9h1"

project = "mlchain"

def readme():
    with open(os.path.join(os.path.dirname(__file__), 'README.rst')) as f:
        return f.read()

def parse_requirements(filename):
    """ load requirements from a pip requirements file """
    lineiter = (line.strip() for line in open(filename))
    return [line for line in lineiter if line and not line.startswith("#")]


extras_require = {
    "core": parse_requirements("requirements/core.txt"),
}

install_requires = set()
for requirements in extras_require.values():
    install_requires.update(requirements)

install_requires = list(install_requires)

setup(
    name=project,
    version=__version__,
    description='MLchain Python Library',
    long_description=readme(),
    url='https://gitlab.com/techainer/ml_platform/mlchain-python',
    author='Techainer Inc.',
    author_email='admin@techainer.com',
    package_data={'mlchain.cli': ['config.yaml'],'mlchain.rpc.server':['static/*','templates/*']},
    include_package_data=True,
    packages=find_packages(exclude=["*.tests", "*.tests.*", "tests.*", "tests"]),
    install_requires=install_requires,
    extras_require=extras_require,
    keywords=['mlchain', 'development', 'deployment ai', 'ai', 'artificial neural network', 'training', 'deploy',
              'deployment', 'monitoring', 'model', 'deep learning', 'machine learning'],
    zip_safe=False,
    setup_requires=[],
    dependency_links=[],
    python_requires='>=3',
    tests_require=[
        "pytest",
        "mock>=1.0.1",
    ],
    py_modules=['mlchain'],
    entry_points={"console_scripts": ["mlchain = mlchain.cli.main:main"]},
    classifiers=[
        'Development Status :: 0.0.1 - Beta',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Libraries',
        'License :: MIT License',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
    ],
)
