import os
import sys

from setuptools import setup

# 'setup.py publish' shortcut.
if sys.argv[-1] == 'publish':
    os.system('python setup.py sdist bdist_wheel')
    os.system('twine upload dist/*')
    sys.exit()

packages = ['wxcadm']

requires = [
    'requests>=2.26.0'
]

with open('README.md', 'r', encoding='utf-8') as f:
    readme = f.read()

setup(
    name='wxcadm',
    version='1.1',
    packages=packages,
    url='https://github.com/kctrey/wxcadm',
    license='GPL-3.0',
    author='Trey Hilyard',
    author_email='kctrey@gmail.com',
    description='A Python 3 Library for Webex Calling Administrators',
    long_description=readme,
    long_description_content_type='text/markdown',
    package_data={'': ['LICENSE']},
    package_dir={'wxcadm': 'wxcadm'},
    include_package_data=True,
    python_requires=">=3.6",
    install_requires=requires
)