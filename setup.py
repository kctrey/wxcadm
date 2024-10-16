import os
import sys

from setuptools import setup

# 'setup.py publish' shortcut.
if sys.argv[-1] == 'publish':
    for f in os.listdir('dist'):
        os.remove("dist/" + f)
    os.system('python setup.py sdist bdist_wheel')
    os.system('twine upload dist/*')
    sys.exit()

packages = ['wxcadm']

requires = [
    'requests==2.32.3',
    'requests-toolbelt>=1.0.0',
    'srvlookup>=2.0.0',
    'xmltodict>=0.12.0',
    'meraki==1.27.0',
    'pyhumps==3.8.0',
    'dataclasses-json>=0.6.4'
]

with open('README.md', 'r', encoding='utf-8') as f:
    readme = f.read()

setup(
    name='wxcadm',
    version='4.3.8',
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
    python_requires=">=3.10",
    install_requires=requires
)
