# -*- coding: utf-8 -*-
"""
* Pizza delivery prompt example
* run example by writing `python example/pizza.py` in your console
"""
from __future__ import print_function, unicode_literals

import regex
from pprint import pprint
import pandas as pd
from PyInquirer import style_from_dict, Token, prompt, Separator
from PyInquirer import Validator, ValidationError
from blessings import Terminal
term = Terminal()
from classes import *

ticker_data = TickerData()
company_data = CompanyData()
ti = time_it()

exchange_source_dict = {
    'nasdaq': 'https://old.nasdaq.com/screening/companies-by-name.aspx?letter=0&exchange=nasdaq&render=download',
    'amex': 'https://old.nasdaq.com/screening/companies-by-name.aspx?letter=0&exchange=amex&render=download',    
    'nyse': 'https://old.nasdaq.com/screening/companies-by-name.aspx?letter=0&exchange=nyse&render=download'} 


#from examples import custom_style_3
print('Stock Search and Query by Christopher M Palmieri')

def SelectAction(actions):
    act_list = actions.keys()
    act_prompt = [
        {
            'type': 'list',
            'name': 'action',
            'message': 'Select Action?',
            'choices': act_list
        } ]
    answer = prompt(act_prompt)
    return actions[answer['action']]()

def SearchTickers(addresses, exchanges, company, sector=None, industry=None):
    """
    Find tickers for company in nasdaq, amex, or nyse\n
    """
    print('searching for tickers in {}'.format(exchanges))
    #dat = pd.concat(map(pd.read_csv, addresses))
    #dat = dat.filter(items=['Symbol', 'Name', 'Sector', 'industry'])
    dat = company_data.GetData(exchanges)

    if sector:
        dat = dat[dat['Sector'].str.contains(sector, na=False, case=False) ]
    if industry:
        dat = dat[dat['industry'].str.contains(industry, na=False, case=False) ]

    dat = dat[dat['Name'].str.contains(company, na=False, case=False) ]
    if len(dat) < 1:
        print('No results for {} found'.format(company))
        return
    lines = dat.to_string(index=False).split('\n')

    ticker_lines = []
    ticker_list = []
    for line in lines[1:]:
        ticker_lines.append({'name': line})
        ticker_list.append(line.split()[0].strip())
    prompt_dict = {
        'type': 'checkbox',
        'qmark': '>',
        'message': 'Select Tickers',
        'name': 'tickers',
        'choices': ticker_lines }

    print('{} items containing "{}" found'.format(
            len(dat), company ))
    print(lines[0])
    results = prompt(prompt_dict)['tickers']
    tickers = [ r.split()[0].strip() for r in results ]
    inverse = prompt( {
        'type': 'rawlist',
        'name': 'inverse',
        'message': 'Add Items',
        'choices': [
            'Add {} Selected'.format(len(results)),
            'Add {} Unselected'.format(len(ticker_list) - len(results)),
            'Add None']
        })['inverse']
    if 'Unselected' in inverse:
        tickers = [ t for t in ticker_list if t not in tickers]
    elif 'None' in inverse:
        tickers = []
    print(tickers)
    return tickers

def AddTickers():
    exchanges = exchange_source_dict 

    exchange_list = []
    for item in exchanges.keys():
        exchange_list.append({'name': item})

    questions = [
        {
            'type': 'checkbox',
            'qmark': '>',
            'message': 'Exchanges to search',
            'name': 'exchanges',
            'choices': exchange_list,
            'validate': lambda answer: 'Must select at least one exchange.' \
                if len(answer) == 0 else True },
        {
            'type': 'input',
            'name': 'company',
            'message': 'Company search string'},
        {
            'type': 'input',
            'name': 'sector',
            'message': 'Sector search string'},
        {
            'type': 'input',
            'name': 'industry',
            'message': 'Industry search string'} ]
    results = prompt(questions)

    if len(results['exchanges']) < 1:
        results['exchanges'] = exchanges # select all if none

    addresses = [ exchanges[select] for select in results['exchanges'] ]
    tickers = SearchTickers(
        addresses, results['exchanges'], results['company'],
        results['sector'], results['industry'])

    ticker_data.Add(tickers)
    return True

def GetCompanyList(tickers):
    ti.Add('getting company list')
    exchanges = exchange_source_dict
    dat = pd.concat(map(pd.read_csv, exchanges.values()))
    ti.Add('csv retrieved')
    dat = dat.filter(items=['Symbol', 'Name'])

    dat.set_index('Symbol', inplace=True)
    return dat.loc[tickers]

def RemoveTickers():
    choice = ticker_data.get_name(False)
    tickers = ticker_data[choice]
    df = company_data.GetNames(tickers)
    lines = df.to_string(index=True).split('\n')

    ticker_lines = []
    ticker_list = []
    for line in lines[2:]:
        ticker_lines.append({'name': line})
        ticker_list.append(line.split()[0].strip())
    prompt_dict = {
        'type': 'checkbox',
        'qmark': '>',
        'message': 'Select Tickers',
        'name': 'tickers',
        'choices': ticker_lines }
    ti.Add('about to prompt')
    results = prompt(prompt_dict)['tickers']
    ti.Add('user replied')
    tickers = [r.split()[0] for r in results]

    inverse = prompt( {
        'type': 'list',
        'name': 'inverse',
        'message': 'Remove Items',
        'choices': [
            'Remove {} Selected'.format(len(tickers)),
            'Remove {} Unselected'.format(len(ticker_list) - len(results)),
            'Remove None']
        })['inverse']
    if 'Unselected' in inverse:
        tickers = [ t for t in ticker_list if t not in tickers]
    elif 'None' in inverse:
        tickers = []
    ticker_data.Filter(choice, tickers)
    print(ti)

    return True

def RemoveList():
    choice = ticker_data.get_name(False)
    confirmation = {
        'type': 'confirm',
        'message': 'Really remove {}?'.format(choice),
        'name': 'yes',
        'default': True }
    if prompt(confirmation)['yes']:
        del ticker_data.ticker_lists[choice]
    return True

def WatchTickers(tickers = None, columns=None, delay=60, times=None):
    'Watch multiple tickers updated regularly'
    import stock_info as yfs
    import time

    max_columns = term.width // 30
    max_rows = term.height - 5
    max_items = max_columns * max_rows
    wanted_rows = int(term.height * .66)

    tickers = ticker_data[ticker_data.get_name()]
    if times:
        tickers = tickers * times
    
    if not columns:
        tickers = tickers[:max_items]
        columns = min(max_columns, len(tickers) // wanted_rows + 1) 

    with term.fullscreen():
        while True:
            print('updating')
            start_time = time.time()
            results = yfs.get_all_prices(tickers)
            outp = []
            for ticker, price in results:
                outp.append('{:6s}: {}'.format(ticker, price))
            ti = time.strftime("%H:%M:%S", time.gmtime())
            print(term.clear() + 'YFIN watching {} tickers: {}'.format(len(tickers), ti))
            print('Press CTRL-C to exit\n')
            print_wide_list(outp, columns)
            end_time = time.time()
            poll = end_time - start_time
            pause = delay - int(poll)
            print('polled in {:.3f}: sleeping {}'.format(
                poll * 1000, pause) )
            if pause > 0:
                try:
                    time.sleep(pause)
                except KeyboardInterrupt:
                    return True
    return True

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


def dummy():
    print('in dummy')
    return True
def exit():
    print('exiting')
    ticker_data.Save()
    return False

actions = {
    'Add Tickers': AddTickers,
    'Remove Tickers': RemoveTickers,
    'Watch Tickers': WatchTickers,
    'Remove List': RemoveList,
    'Exit': exit }

if __name__ == '__main__':
    while SelectAction(actions):
        pass
