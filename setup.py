from distutils.core import setup

setup(
    name='miniutils',
    version='0.0.1',
    packages=['miniutils'],
    url='https://github.com/scnerd/miniutils',
    license='MIT',
    author='scnerd',
    author_email='scnerd@gmail.com',
    description='Small Python utilities for adding concise functionality and usability to your code',
    install_requires=[
        'tqdm',
        'pycontracts',
    ]
)
