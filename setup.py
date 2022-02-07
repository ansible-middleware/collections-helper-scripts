from setuptools import setup

setup(
    name='vars2specs',
    entry_points={
        'console_scripts': [
            'vars2specs = vars2specs:main',
        ],
    }
)
