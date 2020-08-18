from setuptools import setup, find_packages


install_requires = [
    'boto3>=1.5.0',
    'jmespath>=0.7.1,<1.0.0',
    'termcolor>=1.1.0',
    'python-dateutil>=2.4.0'
]


setup(
    name='awslogs',
    version='0.14.0',
    url='https://github.com/jorgebastida/awslogs',
    license='BSD',
    author='Jorge Bastida',
    author_email='me@jorgebastida.com',
    description='awslogs is a simple command line tool to read aws cloudwatch logs.',
    long_description='awslogs is a simple command line tool to read aws cloudwatch logs.',
    keywords="aws logs cloudwatch",
    packages=find_packages(),
    platforms='any',
    python_requires=">=3.5.*",
    install_requires=install_requires,
    test_suite='tests',
    classifiers=[
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
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
