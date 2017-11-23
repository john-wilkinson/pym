#!/usr/bin/env python

from setuptools import setup

setup(
    name='PymApp',
    version='0.1.0',
    description='Python package manager',
    author='John Wilkinson',
    packages=['pym', 'pymcli'],
    package_dir={
        'pym': 'loader',
        'pymcli': 'src'
    },
    entry_points={
        'console_scripts': [
            'pym = pymcli.pym:go'
        ]
    },
    install_requires=[
        'GitPython',
        'wheel'
    ]
)
