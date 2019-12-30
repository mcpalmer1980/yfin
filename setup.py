from setuptools import setup
import concurrent.futures
import threading
setup(
    name='yfin',
    author='Chris Palmieri',
    description='Scrape yahoo financial data using yahoo-fin from the command line',
    version='0.1',
    py_modules=['yfin', 'ticks', 'stock_info', 'classes'],
    install_requires=[
        'Click', 'pandas', 'requests_html', 'Blessings', 'PyInquirer',
    ],
    entry_points='''
        [console_scripts]
        yfin=yfin:main
        ticks=ticks:main
    ''',
)