
import sys
import time
import datetime
import asyncio
import pandas as pd
import click
import stock_info as yfs
import aiohttp
import ticks
import numpy

from scipy import stats
from classes import TickerData, CompanyData, print_wide_list
from blessings import Terminal
from aiohttp import ClientSession

term = Terminal()

not_found = 0
base_url = "https://query1.finance.yahoo.com/v8/finance/chart/"
index_tickers = {
    'sp500': '^GSPC',
    'dow': '^DJI',
    'nasdaq': '^IXIC' }


async def get_exchange_csv():
    exchange_source_dict = {
        'nasdaq': 'https://old.nasdaq.com/screening/companies-by-name.aspx?letter=0&exchange=nasdaq&render=download',
        'amex': 'https://old.nasdaq.com/screening/companies-by-name.aspx?letter=0&exchange=amex&render=download',    
        'nyse': 'https://old.nasdaq.com/screening/companies-by-name.aspx?letter=0&exchange=nyse&render=download'} 
    csv = {}

    async with ClientSession() as session:
        for exchange in exchange_source_dict:
            resp = await session.get(exchange_source_dict[exchange])
            csv[exchange] = await resp.text()
    #print(csv)

async def get_price(ticker, session):
    'Get price, volume, and previous close for ticker'

    response = await session.get(base_url + ticker)
    data =  await response.json()

    try:
        price = data["chart"]["result"][0]["indicators"]["quote"][0]['close'][-1]
        volume = data["chart"]["result"][0]["indicators"]["quote"][0]['volume'][-1]
        pclose = data["chart"]["result"][0]["meta"]["previousClose"]
    except:
        price = not_found
        volume = 0
        pclose = 0
    return ticker, price, volume, pclose

async def get_all_prices(tickers):
    'Get price, volume, and previous close for all items in tickers list'

    async with ClientSession() as session:
        tasks = []
        for tick in tickers:
            tasks.append(get_price(tick, session))
        results = await asyncio.gather(*tasks)
    return results

def get_market_status():
    'Print change and percent change since previous close for each index in index_tickers'

    # generate dictionary for reverse lookup
    ticker_indexes = {v: k for k, v in index_tickers.items()}

    print('\nGetting Index Status at ' + GetTime())
    results = asyncio.run(get_all_prices(index_tickers.values()))
    for ticker, price, volume, closed in results:
        index = ticker_indexes[ticker]
        change = price - closed
        percent = (change / closed) * 100
        print('{}:\t{:+6.2f} / {:.3f}%'.format(index, change, percent))


def get_index_status(tickers, timepoints = 5, delay = 60, save=False):
    'get data for tickers list and run time series analysis for x timepoints'

    print(f"\nScanning {len(tickers)} items over {timepoints} timepoints at {delay} second intervals\n")
    df = pd.DataFrame(columns=[
            'timepoint',
            'ticker',
            'price',
            'volume' ] )
    start_time = time.time()
    first_time = start_time
    for tp in range(timepoints):
        results = asyncio.run(get_all_prices(tickers))
        timepoint = int(start_time - first_time)

        ostr = []
        additions = []
        for ticker, price, volume, closed in results:
            additions.append({
                'timepoint': timepoint,
                'ticker': ticker,
                'price': price,
                'volume': volume})
            ostr.append('{:6s}: {}'.format(ticker, price))

        df = df.append(additions)
        end_time = time.time()
        pause = delay - (end_time - start_time)

        print(term.move_up + 'Data for timepoint {} polled in {:,.0f}ms: sleeping {:.1f}s{}'.format(
            tp+1, (end_time - start_time) * 1000, pause, ' '*10) )

        if pause > 0:
            try:
                time.sleep(pause)
            except KeyboardInterrupt:
                break
        start_time = time.time()

    if save:
        df.to_pickle('dataframe')
    return ProcessTickerData(df)

def get_sector_average_change(prices):
    'Unused function that determined average price change for each sector'

    cd = CompanyData().GetData().set_index('Symbol')
    print('\nAverage change by sector')
    sectors = {}
    for symbol in prices.columns:
        sector = cd.at[symbol, 'Sector']
        if type(sector) == numpy.ndarray: # some tickers return duplicate sectors
            sector = sector[0] # this prevents an error
        change = prices.at['change', symbol]
        sectors[sector] = sectors.get(sector, 0) + change
    
    sdf = pd.Series(sectors)
    print(sdf.to_string())

def get_sector_slopes(prices):
    'Print positive and negative slope data for given prices list'

    cd = CompanyData().GetData().set_index('Symbol')
    print('\nCalculating Sector Details')
    tSectors = {}
    pSectors = {}
    pSectorAvg = {}
    nSectors = {}
    nSectorAvg = {}

    # sort slope data by sector
    for symbol in prices.columns:
        slope = prices.at['slope', symbol]
        sector = cd.at[symbol, 'Sector']
        if type(sector) == numpy.ndarray: # some tickers return duplicate sectors
            sector = sector[0] # this prevents an error

        tSectors[sector] = tSectors.get(sector, 0) + 1
        if slope > 0:
            pSectors[sector] = pSectors.get(sector, 0) + 1
            if not pSectorAvg.get(sector, None):
                pSectorAvg[sector] = []
            pSectorAvg[sector].append(slope)
        
        elif slope < 0:
            nSectors[sector] = nSectors.get(sector, 0) + 1
            if not nSectorAvg.get(sector, None):
                nSectorAvg[sector] = []
            nSectorAvg[sector].append(slope)

    # remove failed/missing tickers that were sorted into nan dictionary   
    if numpy.nan in tSectors:
        del tSectors[numpy.nan]

    # generate dataframe from slope counts and averages
    df = pd.DataFrame(columns = ('Positive Slope', '+Average', 'Negative Slope', '-Average', 'Total') )    
    for sector in sorted(tSectors.keys()):
        pSlopes = int(pSectors.get(sector, 0))
        if sector in pSectorAvg:
            pSlopeAvg = pSectorAvg[sector]
            pSlopeAvg = sum(pSlopeAvg) / len(pSlopeAvg)
        else:
            pSlopeAvg = 0

        nSlopes = (nSectors.get(sector, 0))
        if sector in nSectorAvg:
            nSlopeAvg = nSectorAvg[sector]
            nSlopeAvg = sum(nSlopeAvg) / len(nSlopeAvg)
        else:
            nSlopeAvg = 0

        # add new row to dataframe
        df.loc[sector] = {
                'Positive Slope': pSlopes,
                '+Average': pSlopeAvg,
                'Negative Slope': nSlopes,
                '-Average': nSlopeAvg,
                'Total': tSectors[sector] }

    # display dataframe
    df.loc['Total']= df.sum()
    for column in ('Positive Slope', 'Negative Slope', 'Total'):
        df[column] = df[column].astype(int)
    print(df)

def Regress(dataframe, pivotpoint):
    'Pivot dataframe and append regression info'

    from numpy import float32
    df = dataframe.pivot(
        index = 'timepoint',
        columns = 'ticker',
        values = pivotpoint)

    timepoints = df.index.values
    changes = {}
    slopes = {}
    rvalues = {}
    pvalues = {}
    stderrs = {}

    for p in df:
        results = stats.linregress(timepoints, df[p].astype(float32))
        start = df.at[timepoints[0], p]
        end = df.at[timepoints[-1], p]

        changes[p] = end - start   
        slopes[p] = results.slope
        rvalues[p] = results.rvalue
        pvalues[p] = results.pvalue
        stderrs[p] = results.stderr
    df.loc['change'] = changes
    df.loc['slope'] = slopes
    df.loc['rval'] = rvalues
    df.loc['pval'] = pvalues
    df.loc['sterr'] = stderrs
    return df

def ProcessTickerData(df):
    'Perform time series analysis and display it'

    start = time.time()
    prices = Regress(df, 'price')
    volume = Regress(df, 'volume')
    paverages = prices.iloc[-4:].mean(axis=1)
    vaverages = volume.iloc[-4:].mean(axis=1)

    prices.sort_values('slope', axis=1, inplace=True)
    print(f'Regression processed in: {(time.time() - start) * 1000:.0f}ms')

    # display summary
    print('\nPRICES')
    print(prices)
    print(f'\nStat Average for {prices.shape[1]} tickers')
    print(paverages.to_string(header=False))

    '''
    print()
    print('\nVOLUME')
    print(volume)
    print(f'Stat Average for {prices.shape[1]} tickers')
    print(vaverages.to_string(header=False))
    '''

    return prices, volume

def GetTime():
    return datetime.datetime.now().strftime("%H:%M:%S on %m/%d/%Y")

@click.command()
@click.option('--load', '-l', is_flag=True, help='load data from "dataframe"')
@click.option('--save', '-s', is_flag=True, help='save data to "dataframe"')
@click.option('--interval', '-I', default=60, help='delay between timepoints')
@click.option('--timepoints', '-t', default=5, help='timepoints to use for regression')
@click.option('--index', '-i', default='sp500')
def main(load, save, interval, timepoints, index):
    'Main status command'

    '''
    start = time.time()
    asyncio.run(get_exchange_csv())
    print(time.time() - start)
    start = time.time()
    cd = CompanyData().GetData().set_index('Symbol')
    print(time.time() - start)
    return
    '''

    print('Market Status by Christopher M Palmieri')
    get_market_status()

    td = TickerData(silent=True)
    tickers = td[index]
    assert tickers, f'Index {index} not found: exiting'

    if load:
        print('\nScanning Market Data for 5 minutes...')
        time.sleep(.75)
        print('Debug: using saved data instead')
        time.sleep(.75)
        df = pd.read_pickle('dataframe')
        prices, volumes = ProcessTickerData(df)
    else:
        prices, volumes = get_index_status(tickers, timepoints, interval, save=save)

    #get_sector_average_change(prices)
    get_sector_slopes(prices)

 


if __name__ == '__main__':
    main()