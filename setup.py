import sys

from setuptools import setup, find_packages


install_requires = [
    'boto3>=1.2.1',
    'jmespath>=0.7.1,<1.0.0',
    'termcolor>=1.1.0',
    'python-dateutil>=2.4.0'
]


# as of Python >= 2.7 argparse module is maintained within Python.
extras_require = {
    ':python_version in "2.4, 2.5, 2.6"': ['argparse>=1.1.0'],
}


if 'bdist_wheel' not in sys.argv and sys.version_info < (2, 7):
    install_requires.append('argparse>1.1.0')


setup(
    name='awslogs',
    version='0.8.0',
    url='https://github.com/jorgebastida/awslogs',
    license='BSD',
    author='Jorge Bastida',
    author_email='me@jorgebastida.com',
    description='awslogs is a simple command line tool to read aws cloudwatch logs.',
    long_description='awslogs is a simple command line tool to read aws cloudwatch logs.',
    keywords="aws logs cloudwatch",
    packages=find_packages(),
    platforms='any',
    install_requires=install_requires,
    extras_require=extras_require,
    test_suite='tests',
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
