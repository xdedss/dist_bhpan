
from setuptools import setup, find_packages

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = fh.read()

setup(
    name = 'bhpan',
    version = '0.0.3',
    author = 'LZR',
    license = 'MIT',
    description = 'bhpan commandline tool',
    py_modules = [],
    packages = find_packages(),
    install_requires = [requirements],
    python_requires='>=3.6',
    classifiers=[
        "Operating System :: OS Independent",
    ],
    entry_points = '''
        [console_scripts]
        bhpan=pancli.pancli:main
    '''
)