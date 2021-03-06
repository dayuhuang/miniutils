from setuptools import setup

setup(
    name='miniutils',
    version='0.0.1a6',
    packages=['miniutils'],
    url='http://miniutils.readthedocs.io/en/latest/',
    license='MIT',
    author='scnerd',
    author_email='scnerd@gmail.com',
    description='Small Python utilities for adding concise functionality and usability to your code',
    long_description=open('README.rst').read(),
    install_requires=[
        'tqdm',
        'pycontracts',
        'coloredlogs',
        'astor',
    ],
    download_url='https://github.com/scnerd/miniutils',
    keywords=['miniutils', 'utilities', 'decorators', 'minimal'],
    python_requires='>=3',
)
