import sys, os
import time
import datetime
import asyncio
import pandas as pd
import click
import stock_info as yfs
import aiohttp
import numpy
from blessings import Terminal
from PyInquirer import prompt
from aiohttp import ClientSession
from scipy import stats
from classes import *
from collections import OrderedDict
import ticks
import ibx

market_state = None
company_data = CompanyData()
ticker_data = TickerData(silent=True)
term = Terminal()


index_tickers = {
    'sp500ticker': '^GSPC',
    'dow': '^DJI',
    'nasdaq': '^IXIC' }

index_tickers = {
    'sp500': '^GSPC',
    'dow': '^DJI',
    'nasdaq': '^IXIC' }

exchange_source_dict = {
    'nasdaq': 'https://old.nasdaq.com/screening/companies-by-name.aspx?letter=0&exchange=nasdaq&render=download',
    'amex': 'https://old.nasdaq.com/screening/companies-by-name.aspx?letter=0&exchange=amex&render=download',    
    'nyse': 'https://old.nasdaq.com/screening/companies-by-name.aspx?letter=0&exchange=nyse&render=download'} 

not_found = 0
base_url = "https://query1.finance.yahoo.com/v8/finance/chart/"
ib = ibx.ibx(False, allow_error=True)
