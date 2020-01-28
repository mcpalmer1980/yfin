#! /usr/bin/env python3
from common import *
import common
import ticks
import handlers
import ibx

running = True
marketState = None



def get_stock_buy_list():
    if os.getenv('stock_buy'):
        return os.getenv('stock_buy')
    else:
        return ticker_data.get_name(create=True)
        

async def get_price(ticker, session):
    'Get price, volume, and previous close for ticker'

    response = await session.get(base_url + ticker)
    data =  await response.json()

    try:
        price = data["chart"]["result"][0]["meta"]["regularMarketPrice"]
        pclose = data["chart"]["result"][0]["meta"]["previousClose"]
        volumes = data["chart"]["result"][0]["indicators"]["quote"][0]['volume']
        volume = next((v for v in reversed(volumes) if v), 0) # get most recent non-empty item, def=0 to avoid exception
        #volumes[-1] or volumes[-2] or volumes[-3] or volumes[-4] # the last items are often empty?
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


def scan_index(tickers, timepoints = 5, delay = 60, save=False):
    'get data for tickers list and run time series analysis for x timepoints'

    global running
    space = ' ' * 20
    print(f"\nScanning {len(tickers)} items over {timepoints} timepoints at {delay} second intervals\n\n")
    outstr = 'Awaiting first timepoint results'
    df = pd.DataFrame(columns=[
            'timepoint',
            'ticker',
            'price',
            'volume' ] )
    start_time = time.time()
    first_time = start_time
    for tp in range(timepoints):
        print(term.move_up*2 + outstr + space)
        print('Collecting data... Please wait' + space)
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

        outstr = 'Data for timepoint {} polled in {:,.0f}ms: sleeping {:.1f}s{}'.format(
            tp+1, (end_time - start_time) * 1000, pause, ' '*10)
        print(term.move_up*2 + outstr + space)
        print('Waiting: press CTRL-C to cancel' + space)

        if pause > 0:
            try:
                time.sleep(pause)
            except KeyboardInterrupt:
                print('canceled while waiting')
                running = False
                break
        start_time = time.time()

    if save:
        print('data saved to dataframe.sav')
        df.to_pickle('dataframe.sav')
    return df

def get_sector_slopes(prices):
    'Print positive and negative slope data for given prices list'

    print('\nCalculating Sector Details')
    df = prices
    sectors = pd.DataFrame(columns = ('pslope', 'pavg', 'nslope', 'navg', 'count', '%pslope'))
    for sector in sorted(prices['sector'].drop_duplicates().dropna()):
        count = len(prices.loc[prices['sector'] == sector])
        pslopes = prices.loc[(prices['sector'] == sector) & (prices['slope'] > 0)]
        nslopes = prices.loc[(prices['sector'] == sector) & (prices['slope'] > 0)]

        sectors.loc[sector] = {
            'pslope': len(pslopes),
            'pavg': pslopes.slope.mean(),
            'nslope': len(nslopes),
            'navg': nslopes.slope.mean(),
            'count': count,
            '%pslope': (len(pslopes) / count) * 100 }
    total = sectors.sum()
    sectors.loc['Average'] = sectors.mean()
    sectors.loc['Total'] = total
    print(sectors)
    return sectors

def detect_state(prices, sectors):
    pslope = sectors.at['Total', '%pslope']
    if pslope < 15:
        state = 'down'
    elif pslope < 45:
        state = 'downtrend'
    elif pslope < 65:
        state = 'random'
    elif pslope < 85:
        state = 'uptrend'
    else:
        state = 'up'
    return state

def save_xls(long, prices, sectors):
    print('saving data to market.xlsx')
    with pd.ExcelWriter('market.xlsx') as writer:  # doctest: +SKIP
        long.to_excel(writer, sheet_name='long')
        prices.to_excel(writer, sheet_name='prices')
        sectors.to_excel(writer, sheet_name='sectors')

def ProcessTickerData(dataframe):
    'Pivot dataframe and append regression info'

    def regression(row):
        # called by dataframe.apply to regress each row

        try:
            '''
            there are 3 problems with the company data that must be accounted for
            1: missing values will trigger a key error
                the try ... except clause handles this issue
            2: empty data or na can be returned,
                I added "or 'Unknown Sector'" to label empty datums
            3: some stocks return a strange list such as ['Technolgy', 'Technology']
                so if sector is not a str I get the first entry from the list instead
            '''            
            sector = cd.at[row.name, 'Sector'] or 'Unknown Sector'
            sector = sector if type(sector) == str else sector[0]
        except:
            sector = 'Unknown Sector'
        r = stats.linregress(timepoints, y=row)
        return pd.Series(oDict((
            ('change', row.iloc[-1] - row.iloc[0]), # change from first to last timepoint
            ('slope', r.slope),
            ('rvalue', r.rvalue),
            ('pvalue', r.pvalue),
            ('stderr', r.stderr),
            ('sector', sector) )))

    prices = dataframe.pivot(
        index = 'ticker',
        columns = 'timepoint',
        values = 'price')
    volumes = dataframe.pivot(
        index = 'ticker',
        columns = 'timepoint',
        values = 'volume')

    cd = company_data.GetData().set_index('Symbol') # used for sector look-up by ticker
    timepoints = prices.columns.values # y values for regression
    results = prices.apply(regression,axis=1) # apply price regression
    results = results.join(volumes.mean(axis=1).rename('volume')) # add average volume column
    results.sort_values('slope', axis=0, inplace=True)
    results.loc['Average']= results.mean()
    print(results)
    return results

def GetTime():
    return datetime.datetime.now().strftime("%H:%M:%S on %m/%d/%Y")

@click.command()
@click.option('--load', '-l', is_flag=True, help='load data from "dataframe"')
@click.option('--save', '-s', is_flag=True, help='save data to "dataframe"')
@click.option('--interval', '-I', default=60, help='delay between timepoints')
@click.option('--timepoints', '-t', default=5, help='timepoints to use for regression')
@click.option('--index', '-i', default='sp500', help='index or ticker list to scan: def=sp500')
@click.option('--excel', '-x', is_flag=True, help='save data to dataframe.xls')
def main(load, save, interval, timepoints, index, excel):
    'Main status command'

    print('Market Status by Christopher M Palmieri')
    ib.Connect(allow_error=True)
    #stock_buy_list = get_stock_buy_list()
    #print(stock_buy_list)

    running = False
    first_time = True
    while running or first_time:
        first_time = False
        get_market_status()

        tickers = ticker_data[index]
        assert tickers, f'Index {index} not found: exiting'

        if load:
            print('\nLoading saved data from dataframe.sav')
            df = pd.read_pickle('dataframe.sav')
            stocks = ProcessTickerData(df)
        else:
            df = scan_index(tickers, timepoints, interval, save=save)
            stocks = ProcessTickerData(df)

        sectors = get_sector_slopes(stocks)
        handlers.launch(stocks, sectors)

    if excel: save_xls(df, stocks, sectors)


 


if __name__ == '__main__':
    main()