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
	entry_points = {
		'console_scripts': [
			'vesna_multiplex = vesna.multiplex:main'
		]
	},
	test_suite = 'tests',
)
