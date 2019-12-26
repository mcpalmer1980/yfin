# -*- coding: utf-8 -*-
"""
* Pizza delivery prompt example
* run example by writing `python example/pizza.py` in your console
"""
from __future__ import print_function, unicode_literals

import regex
from pprint import pprint

from PyInquirer import style_from_dict, Token, prompt, Separator
from PyInquirer import Validator, ValidationError

#from examples import custom_style_3
print('Stock Search and Query')

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
    actions[answer['action']]()


def SearchTickers(where, what, sector=None, industry=None):
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
        lines = dat.to_string(index=False).split('\n')

        ticker_list = []
        for line in lines[1:]:
            ticker_list.append({'name': line})
        prompt_dict = {
            'type': 'checkbox',
            'qmark': '>',
            'message': 'Select Tickers',
            'name': 'tickers',
            'choices': ticker_list }

        print('{} items containing "{}" found in {}'.format(
                len(dat), what, exchange))
        print(lines[0])
        results = prompt(prompt_dict)



    import pandas as pd
    for exchange in exchanges:
        # find first exchange that starts with query string        
        if exchange.startswith(where.lower()):
            print('searching for tickers in ' + exchange)
            dat = pd.read_csv(exchanges[exchange]).filter(items=['Symbol', 'Name', 'Sector', 'industry'])

            show_results(dat, what, exchange, sector, industry)
            break

def AddTickers():
    exchanges = {
        'nasdaq': 'https://old.nasdaq.com/screening/companies-by-name.aspx?letter=0&exchange=nasdaq&render=download',
        'amex': 'https://old.nasdaq.com/screening/companies-by-name.aspx?letter=0&exchange=amex&render=download',    
        'nyse': 'https://old.nasdaq.com/screening/companies-by-name.aspx?letter=0&exchange=nyse&render=download'} 

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
            'message': 'Sector search string'} ]
    results = prompt(questions)

    if len(results['exchanges']) < 1:
        print('Must search at least 1 exchange')
        return
    exchange = results['exchanges'][0]
    SearchTickers(
        exchange, results['company'],
        results['sector'], results['industry'])

def dummy():
    print('in dummy')
    return False

actions = {
    'Add Tickers': AddTickers,
    'Remove Tickers': dummy,
    'Watch Tickers': dummy }

SelectAction(actions)
