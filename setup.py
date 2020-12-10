import re

from setuptools import find_packages
from setuptools import setup

with open('fcb/__init__.py', 'rt', encoding='utf-8') as f:
    version = re.search(r"__version__ = '(.*?)'", f.read()).group(1)

setup(name='fcb',
      version=version,
      description='Flask celery boilerplate project.',
      url='https://github.com/sdg32/flask-celery-boilerplate',
      author='sdg32',
      packages=find_packages(exclude=['*.tests', '*.tests.*',
                                      'tests.*', 'tests']),
      include_package_data=True,
      zip_safe=False,
      python_requires='~=3.9.0',
      install_requires=[
          'celery[redis]~=5.0.4',
          'click~=7.1.2',
          'flask~=1.1.2',
          'flask-sqlalchemy~=2.4.4',
          'redis~=3.5.3',
          'sqlalchemy~=1.3.20',
          'werkzeug~=1.0.1',
      ],
      tests_require=[],
      extras_require={})
