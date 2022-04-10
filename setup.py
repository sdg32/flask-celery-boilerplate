import re

from setuptools import find_packages
from setuptools import setup

with open('fcb/__init__.py', 'rt', encoding='utf-8') as f:
    version = re.search(r"__version__ = '(.*?)'", f.read()).group(1)

setup(
    name='fcb',
    version=version,
    description='Flask celery boilerplate project.',
    url='https://github.com/sdg32/flask-celery-boilerplate',
    author='sdg32',
    packages=find_packages(exclude=['*.tests', '*.tests.*',
                                    'tests.*', 'tests']),
    include_package_data=True,
    zip_safe=False,
    python_requires='~=3.10.0',
    install_requires=[
        'celery[redis]~=5.2.6',
        'click~=8.1.2',
        'flask~=2.1.1',
        'flask-sqlalchemy~=2.5.1',
        'redis~=4.2.2',
        'python-dotenv~=0.20.0',
        'sqlalchemy~=1.4.35',
        'werkzeug~=2.1.1',
    ],
    tests_require=[],
    extras_require={
        'dev': [
            'mypy',
        ],
    },
)
