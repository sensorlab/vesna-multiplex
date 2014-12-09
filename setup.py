#!/usr/bin/python

from setuptools import setup

setup(name='vesna_multiplex',
	version='1.0.0',
	description='Multiplex a TCP connection to multiple clients.',
	license='GPL',
	long_description=open("README.rst").read(),
	author='Tomaz Solc',
	author_email='tomaz.solc@ijs.si',
	packages = [ 'vesna' ],
	test_suite = 'tests',
)
