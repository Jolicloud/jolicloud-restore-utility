#!/usr/bin/env python
# -*- coding: utf-8 -*-

import glob

from setuptools import setup, find_packages

setup(
    name='jolicloud-restore-utility',
    version='0.1',
    description='Jolicloud',
    author=u'Jérémy Bethmont',
    author_email='jerem@jolicloud.org',
    url='http://www.jolicloud.com/',
    scripts = ['jolicloud-restore-utility'],
    data_files=[
        #('share/jolicloud-upgrader', glob.glob("ui/*.ui") + glob.glob("ui/*.png")),
        #('/etc/sudoers.d', ['etc/sudoers.d/jolicloud-upgrader'])
    ],
    packages=find_packages(),
)
