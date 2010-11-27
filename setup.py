#!/usr/bin/python

from distutils.core import setup

setup(name='Jolicloud Restore Utility',
    version='0.1',
    license='GPL v2',
    author='Jolicloud Developers',
    author_email='developers@jolicloud.org',
    packages=['jolicloud_restore_utility'],
    scripts=['jolicloud-restore-utility'],
    package_data={'jolicloud_restore_utility': ['*.glade']})
