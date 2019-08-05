from distutils.core import setup
import os

setup(
	name='MQDQParser',
	version='0.1',
	author='Ben Nagy',
	packages=['mqdq'],
	license='3-Clause BSD',
	url='https://github.com/bnagy/mqdq-parser',
	long_description=open(os.path.join(os.path.dirname(__file__), 'README.txt')).read(),
	install_requires=[
		'BeautifulSoup',
		'numpy',
		'scipy',
		'pandas'
	]
)
