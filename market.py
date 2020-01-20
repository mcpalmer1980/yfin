import ib_insync as ibi
import asyncio
import sys
import time

import pandas as pd
import stock_info as yfs
from classes import TickerData, CompanyData

import click
from blessings import Terminal
from PyInquirer import style_from_dict, Token, prompt, Separator
from PyInquirer import Validator, ValidationError

term = Terminal()
print = click.echo
describe = click.echo

index_tickers = {
    'sp500': '^GSPC',
    'dow': '^DJI',
    'nasdaq': '^IXIC' }

@click.command()
def main():
    import ticks, numpy

    print('Market Status by Christopher M Palmieri')
    print('Getting Index Status')
    for index in index_tickers:
        ticker = index_tickers[index]
        closed = float(get_info(ticker, 'previous cl'))
        price = yfs.get_live_price(ticker)
        change = price - closed
        percent = (change / closed) * 100
        print('{}:\t{:+6.2f}/{:.3f}'.format(index, change, percent))


    print('\nScanning Market Data for 5 minutes...')
    time.sleep(.75)
    print('Debug: using saved data instead')
    time.sleep(.75)
    df = pd.read_pickle('dataframe')
    prices, volumes = ticks.ProcessTickerData(df)

    print()
    cd = CompanyData().GetData().set_index('Symbol')
    print('Calculating Sector Totals')
    sectors = {}
    for symbol in prices.columns:
        sector = cd.at[symbol, 'Sector']
        if type(sector) == numpy.ndarray: # some tickers return duplicate sectors
            sector = sector[0] # this prevents an error
        change = prices.at['change', symbol]
        sectors[sector] = sectors.get(sector, 0) + change


    
    sdf = pd.Series(sectors)
    print(sdf.to_string())


def get_info(ticker, item):
    'Get info from stock ticker'

        
    results = yfs.get_stats(ticker) 
    results = results[results['Attribute'].str.contains(item, na=False, case=False) ]
    return results.Value

if __name__ == '__main__':
    main()
