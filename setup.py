from setuptools import setup
import concurrent.futures
import threading
setup(
    name='yfin',
    author='Chris Palmieri',
    description='Scrape yahoo financial data using yahoo-fin from the command line',
    version='0.1',
    py_modules=['yfin', 'stock_info'],
    install_requires=[
        'Click', 'pandas', 'requests_html', 'Blessings',
    ],
    entry_points='''
        [console_scripts]
        yfin=yfin:main
    ''',
)