#! /usr/bin/env python3

import click
from blessings import Terminal
import pandas as pd
import stock_info as yfs


term = Terminal()
print = click.echo
describe = click.echo

def time_it(desc, ti=None):
    if ti:
        ti, desc = ti
        ti.append(time.time() - ti[0])
        desc.append(desc)
        return ti, desc
    else:
        return time.time(), desc

def print_wide_list(l, columns=3, pager=False):
    height = len(l) // columns
    width = term.width // columns
    if len(l) > height * columns:
        height += 1
        l += [''] * (height * columns - len(l))

    if pager:
        lines = ''
        for row in range(height):
            for col in range(columns):
                item = l[int(row + col * (height))]
                lines += item + ' ' * (width - len(item))
            lines += '\n'
        click.echo_via_pager(lines)
    else:
        for row in range(height):
            line = ''
            for col in range(columns):
                item = l[int(row + col * (height))]
                line += item + ' ' * (width - len(item))
            print(line)


@click.group()
def main():
    """
    Simple CLI for querying Yahoo Finance by Christopher Palmieri

    use yfin COMMAND --help for details about a sub-command
    """
    pass

@main.command()
@click.argument('query', nargs=-1)
def price(query,):
    """Find the current stock price of given stock ticker(s)"""
    for ticker in query:
            price = yfs.get_live_price(ticker)
            print(term.reverse(ticker) + ':\t{}'.format(price))
    return
    for ticker in query:
        try:
            price = yfs.get_live_price(ticker)
            print(term.reverse(ticker) + ':\t{}'.format(price))
        except:
            print(ticker + ':\t'  + term.red('not found'))

@main.command()
@click.argument('query', nargs=-1)
@click.option('--columns', '-c', default=1, help='columns to show')
@click.option('--delay', '-d', default = 30, help='delay between updates (30s minimum)')
@click.option('--times', '-t', default=1, help='multiply the query list for testing')
def watch(query, columns, delay, times):
    'Watch multiple tickers updated regularly'
    import time
    query = query * times
    #delay = max(delay, 30) if delay else 30
    with term.fullscreen():
        while True:
            start_time = time.time()
            results = yfs.get_all_prices(query)
            outp = []
            for ticker, price in results:
                outp.append('{:6s}: {}'.format(ticker, price))
            ti = time.strftime("%H:%M:%S", time.gmtime())
            print(term.clear() + 'YFIN watching {} tickers: {}'.format(len(query), ti))
            print('Press CTRL-C to exit\n')
            print_wide_list(outp, columns)
            end_time = time.time()
            poll = end_time - start_time
            pause = delay - int(poll)
            print('polled in {:.3f}: sleeping {}'.format(
                poll * 1000, pause) )
            if pause > 0:
              time.sleep(pause)

@main.command()
@click.argument('query', nargs=-1)
@click.option('--times', '-t', default=0, help='multiply the query list for longer testing')
@click.option('--workers', '-w', default=10, help='number of worker threads for testing (10 def)')
def test(query, times, workers):
    'Test serial vs concurrent stock price query speed'
    query = query * times
    print('polling {} items with {} concurrent workers'.format(len(query), workers))
    ti = yfs.time_it()
    results = yfs.get_all_prices(query, workers)
    ti.add('polled concurrently')
    print(ti)
    print('polling {} items serially'.format(len(query)))
    results = yfs.get_all_prices_slow(query)
    ti.add('polled serially')
    print(ti)

@main.command()
@click.argument('query')
@click.option('--filter', '-F', 'filter_', help='filter results (start. .end or all)', default='')
@click.option('--from', '-f', 'from_', help='first entry to show', default=0)
@click.option('--to', '-t', help='last entry to show', default=0 )
@click.option('--columns', '-c', help='columns to show', default=3 )
@click.option('--pager', '-p', is_flag=True, help='display output in scrolling pager')
def list(query, filter_, from_, to, columns, pager):
    """List stock tickers from given exchange(dow, nasdaq, sp500, other)"""

    exchanges = {
            'dow': yfs.tickers_dow,
            'nasdaq': yfs.tickers_nasdaq,
            'sp500': yfs.tickers_sp500,
            'other':yfs.tickers_other }

    for exchange in exchanges:
        # find first exchange that starts with query string        
        if exchange.startswith(query.lower()):
            print('querying ' + exchange)
            results = exchanges[exchange]()
            if filter_:
                print('filtering results by ' + filter_)
                if filter_.endswith('.'):
                    filter_ = filter_[:-1]
                    results = [r for r in results if r.lower().startswith(filter_.lower()) ]
                elif filter_.startswith('.'):
                    filter_ = filter_[1:]
                    results = [r for r in results if r.lower().endswith(filter_.lower()) ]
                else:
                    results = [r for r in results if filter_.lower() in r.lower() ]
            if to or from_:
                to = to or len(results)     
                print('printing items from {} to {}'.format(from_, to))
                print_wide_list(results[from_:to], columns, pager)
            else:
                print('printing {} found items'.format(len(results)))
                print_wide_list(results, columns, pager)
            break
    else:
        print('exchange not found')



@main.command()
@click.argument('where')#, help='Search in nasdaq, amex, nyse, or all')
@click.argument('what')# help='Search for given string in company name')
@click.option('--sector', '-s', help='filter by sector', default='')
@click.option('--industry', '-i', help='filter by industry', default='')
def search(where, what, sector, industry):
    """
    Find tickers for company in nasdaq, amex, or nyse\n
    
    WHERE:\texchange to search can be nasdaq, amex, nyse, or all\n
    WHAT:\tsearch string can be a regular expression
    """
    exchanges = {
        'nasdaq': 'https://old.nasdaq.com/screening/companies-by-name.aspx?letter=0&exchange=nasdaq&render=download',
        'amex': 'https://old.nasdaq.com/screening/companies-by-name.aspx?letter=0&exchange=amex&render=download',    
        'nyse': 'https://old.nasdaq.com/screening/companies-by-name.aspx?letter=0&exchange=nyse&render=download'}

    def show_results(dat, what, exchange, sector, industry):
        if sector:
            dat = dat[dat['Sector'].str.contains(sector, na=False, case=False) ]
        if industry:
            dat = dat[dat['industry'].str.contains(industry, na=False, case=False) ]

        dat = dat[dat['Name'].str.contains(what, na=False, case=False) ]
        print(dat.to_string(index=False))
        print('{} items containing "{}" found in {}'.format(
                len(dat), what, exchange))

    import pandas as pd
    for exchange in exchanges:
        # find first exchange that starts with query string        
        if exchange.startswith(where.lower()):
            print('searching for tickers in ' + exchange)
            dat = pd.read_csv(exchanges[exchange]).filter(items=['Symbol', 'Name', 'Sector', 'industry'])

            show_results(dat, what, exchange, sector, industry)
            break
    else:
        if where == 'all':
            print('searching for tickers in all exchanges')
            dat = pd.concat(map(pd.read_csv, exchanges.values()))
            dat = dat.filter(items=['Symbol', 'Name', 'Sector', 'industry'])

            show_results(dat, what, 'all', sector, industry)
        else:
            print('exchange not found')


@main.command()
@click.option('--from', '-f', 'from_', help='first entry to show', default=0)
@click.option('--to', '-t', help='last entry to show', default=10 )
@click.option('--pager', '-p', is_flag=True, help='display all entries in scrolling pager')
def winners(from_, to, pager):
    "Show day's biggest price winners"
    results = yfs.get_day_gainers()
    results.rename({
            'Price (Intraday)': 'Intraday', 'Avg Vol (3 month)': '3mo Average',
            'PE Ratio (TTM)': 'PE Ratio' }, axis = 'columns', inplace = True)
    if pager:
        click.echo_via_pager(results.to_string(index=False))
    else:
        print('printing items {}-{} of {}'.format(from_, to, len(results)))
        print(results[from_:to].to_string(index=False))


@main.command()
@click.option('--from', '-f', 'from_', help='first entry to show', default=0)
@click.option('--to', '-t', help='last entry to show', default=10 )
@click.option('--pager', '-p', is_flag=True, help='display all entries in scrolling pager')
def losers(from_, to, pager):
    "Show day's biggest price losers"
    results = yfs.get_day_gainers()
    results.rename({
            'Price (Intraday)': 'Intraday', 'Avg Vol (3 month)': '3mo Average',
            'PE Ratio (TTM)': 'PE Ratio' }, axis = 'columns', inplace = True)
    if pager:
        click.echo_via_pager(results.to_string(index=False))
    else:
        print('printing items {}-{} of {}'.format(from_, to, len(results)))
        print(results[from_:to].to_string(index=False))

@main.command()
@click.option('--from', '-f', 'from_', help='first entry to show', default=0)
@click.option('--to', '-t', help='last entry to show', default=10 )
@click.option('--pager', '-p', is_flag=True, help='display all entries in scrolling pager')
def active(from_, to, pager):
    "Print day's most active stocks"

    results = yfs.get_day_most_active()
    results.rename({
            'Price (Intraday)': 'Intraday', 'Avg Vol (3 month)': '3mo Average',
            'PE Ratio (TTM)': 'PE Ratio' }, axis = 'columns', inplace = True)
    if pager:
        click.echo_via_pager(results.to_string(index=False))
    else:
        print('printing items {}-{} of {}'.format(from_, to, len(results)))
        print(results[from_:to].to_string(index=False))


@main.command()
@click.argument('ticker')
def info(ticker):
    'Print analyst info by stock ticker'
    print(yfs.get_analysts_info(ticker))
@main.command()
@click.argument('ticker')
def cash(ticker):
    'Print cash flow by stock ticker'
    print(yfs.get_cash_flow(ticker))
@main.command()
@click.argument('ticker')
def holders(ticker):
    'Print major stock holders by ticker'
    holders_site = "https://finance.yahoo.com/quote/" + \
                    ticker + "/holders?p=" + ticker
    tables = pd.read_html(holders_site , header = 0)
    for table, title in zip(tables, (
            'Major Holders', 'Top Institutional', 'Top Mutual')):
        print(title)
        print(table.to_string(index=False))
        print()

@main.command()
@click.argument('ticker')
@click.option('filter', '-f', default='', help='Filter results rows by string data')
@click.option('line', '-l', default=0, help='Print the value of a given line number')
@click.option('LINE', '-L', default=0, help='Print attribute and value of line number')
def stats(ticker, filter, line, LINE):
    'Print stats by stock ticker'
    results = yfs.get_stats(ticker)
    if line:
        val = results.at[line, 'Value']
        print(val)
    elif LINE:
        attr = results.at[LINE, 'Attribute']
        val = results.at[LINE, 'Value']
        print('{}: {}'.format(attr, val))
    elif filter:
        results = results[results['Attribute'].str.contains(filter, na=False, case=False) ]
        print(results)

@main.command()
@click.argument('ticker')
@click.option('--last', '-l', default=30, help='Print previous X days')
@click.option('--from', '-f', 'from_', help='first date to show', default='')
@click.option('--to', '-t', help='last date to show', default='' )
@click.option('--pager', '-p', is_flag=True, help='display output in scrolling pager')
def data(ticker, last, from_, to, pager):
    'Print historical price data'
    last = last or 30
    pd.set_option('display.max_rows', 180)
    results = yfs.get_data(ticker)
    if from_ and to:
        describe('printing items between {} and {}'.format(from_, to))
        results = results.loc[from_:to]
    elif from_:
        describe('printing items after ' + from_)
        results = results.loc[from_:]
    elif to:
        describe('printing items before ' + to)
        results = results.loc[:to]
    else:
        describe('printing last {} days'.format(last))
        results = results.iloc[::-1]
        results = results[:last]
    
    if pager:
        click.echo_via_pager(results.to_string())
    else:
        print(results)


@main.command()
@click.argument('ticker')
@click.option('line', '-l', default=0, help='Print the value of a given line number')
@click.option('LINE', '-L', default=0, help='Print attribute and value of line number')
def quote(ticker, line, LINE):
    'print quote data for given stock ticker'
    results = yfs.get_quote_table(ticker, False)
    if line:
        val = results.at[line, 'value']
        print(val)
    elif LINE:
        attr = results.at[LINE, 'attribute']
        val = results.at[LINE, 'value']
        print('{}: {}'.format(attr, val))
    else:
        print(results)



if __name__ == '__main__':
    main()
'''
get_quote_table - convert dict somehow

holders - clean up alignment?
'''    