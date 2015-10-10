import sys

from setuptools import setup, find_packages

install_requires = [
    'jmespath==0.7.1',
    'botocore<=1.2.3',
    'boto3>1.0.0',
    'termcolor>=1.1.0',
    'python-dateutil>=2.4.0'
]

tests_require = []

# as of Python >= 2.7 argparse module is maintained within Python.
if sys.version_info < (2, 7):
    install_requires.append('argparse>=1.1.0')

# as of Python >= 3.3 unittest.mock module is maintained within Python.
if sys.version_info < (3, 3):
    tests_require.append('pbr>=0.11,<1.7.0')
    tests_require.append('mock>=1.0.0')

setup(
    name='awslogs',
    version='0.1.0',
    url='http://github.com/jorgebastida/awslogs',
    license='BSD',
    author='Jorge Bastida',
    author_email='me@jorgebastida.com',
    description='awslogs is a simple command line tool to read aws cloudwatch logs.',
    long_description='awslogs is a simple command line tool to read aws cloudwatch logs.',
    keywords="aws logs cloudwatch",
    packages=find_packages(),
    platforms='any',
    install_requires=install_requires,
    test_suite='tests',
    tests_require=tests_require,
    classifiers=[
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 2',
        'Development Status :: 4 - Beta',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Topic :: Utilities'
    ],
    entry_points={
        'console_scripts': [
            'awslogs = awslogs.bin:main',
        ]
    },
    zip_safe=False
)
