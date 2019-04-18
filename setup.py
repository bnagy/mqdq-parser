from distutils.core import setup
import os

setup(
	name='MQDQParser',
	version='0.1dev',
	packages=['mqdq',],
	license='3-Clause BSD',
	long_description=open(os.path.join(os.path.dirname(__file__), 'README.txt')).read(),
)
