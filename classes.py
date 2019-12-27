import pandas as pd
from PyInquirer import style_from_dict, Token, prompt, Separator
from PyInquirer import Validator, ValidationError
import time

exchange_source_dict = {
    'nasdaq': 'https://old.nasdaq.com/screening/companies-by-name.aspx?letter=0&exchange=nasdaq&render=download',
    'amex': 'https://old.nasdaq.com/screening/companies-by-name.aspx?letter=0&exchange=amex&render=download',    
    'nyse': 'https://old.nasdaq.com/screening/companies-by-name.aspx?letter=0&exchange=nyse&render=download'} 

class time_it():
    def __init__(self, desc=False):
        self.last_time = time.time()
        self.first_time = self.last_time
        self.desc = []
        self.time = []
        self.total = []
        if desc:
            self.add(desc, True)

    def Add(self, desc, blank=False):
        new = time.time()
        self.desc.append(desc)
        if blank:
            self.time.append(0)
            self.total.append(0)
        else:
            self.time.append(new - self.last_time)
            self.total.append(new - self.first_time)        
        self.last_time = new

    def New(self, desc):
        print(self)
        self.__init__(desc)

    def __str__(self):
        ma = len(max(self.desc, key=len)) + 3
        st = ''
        for desc, ti, tot in zip(self.desc, self.time, self.total):
            left = desc + ' ' * (ma - len(desc))
            if ti:
                st += '{}: {:06.2f}\t{:06.2f}\n'.format(
                    left, ti*1000, tot*1000)
            else:
                st += str(desc) + '\n'
        self.__init__()
        return st

class TickerData():
    """
    Maintans a list of ticker lists
    Defaults to 'tickers.dat'
    Stores each list as one line in a tab seperated text file
    The list's descriptive title is stored in column 1
    """

    def __init__(self, filename = 'tickers.dat', silent=False):
        """
        Initialize ticker lists
        try to load from filename (def = tickers.dat)
        """
        self.ticker_lists = {}
        try:
            with open(filename, 'r') as f:
                lines = f.readlines()
        except IOError as err:
            if not silent:
                print('failed to load list data')
            lines = []
        for line in lines:
            if line.strip():
                items = line.strip().split('\t')
                self.ticker_lists[items[0]] = items[1:]
        else:
            if not silent:
                print('loaded {} stock lists from {}'.format(len(self.ticker_lists), filename))
    def __getitem__(self, index):
        if index in self.ticker_lists:
            return self.ticker_lists[index]
        else:
            return []

    def Add(self, tickers):
        """
        Display a prompt for users to select a list
        Add tickers to the selected list
        """
        if tickers:
            name = self.get_name()
            if name in self.ticker_lists:
                self.ticker_lists[name] += [
                    t for t in tickers if t not in self.ticker_lists[name] ]
            else:
                self.ticker_lists[name] = tickers

    def Filter(self, name, items):
        """
        Remove items from named ticker_list
        """
        if name in self.ticker_lists:
            self.ticker_lists[name] = [
                t for t in self.ticker_lists[name] if t not in items]

    def Save(self, filename = 'tickers.dat'):
        """
        Save the ticker lists to filename (def = tickers.dat)
        """
        print('saving {} stock lists to {}'.format(len(self.ticker_lists), filename))
        try:
            with open(filename, 'w') as f:
                for item in self.ticker_lists:
                    line = '\t'.join(self.ticker_lists[item])
                    if line and item:
                        print(item + '\t' + line, file=f)
        except IOError as err:
            print('failed to save list data')
            
    def get_name(self, new = True):
        """
        Prompt user to select a list
        show 'New List' at the top of list unles new=False
        """
        choices = list(self.ticker_lists.keys())
        if new: choices = ['New List'] + choices

        question = [{
            'type': 'list',
            'name': 'choice',
            'message': 'Select list to add tickers',
            'choices': choices }]
        choice = prompt(question)['choice']
        if choice == 'New List':
            question = [{
                'type': 'input',
                'name': 'input',
                'message': 'List to add tickers to'}]
            return prompt(question)['input']    
        else:
            return choice or 'default'

class CompanyData():
    def __init__(self):
        self.loaded = False

    def retrieve_data(self):
        print('downloading company data')
        exchanges = exchange_source_dict
        #self.company_data = pd.concat(map(pd.read_csv, exchanges.values()))

        dfs = []
        for exchange in exchanges:
            df = pd.read_csv(exchanges[exchange])
            df['Exchange'] = exchange
            dfs.append(df)
        self.company_data = pd.concat(dfs)

        df = self.company_data.filter(items=['Symbol', 'Name', 'Exchange'])
        df.set_index('Symbol', inplace=True)
        self.company_names = df
        self.loaded = True

    def GetNames(self, tickers):
        if not self.loaded:
            self.retrieve_data()

        df = self.company_names.loc[tickers]
        return df

    def GetData(self, exchanges):
        if not self.loaded:
            self.retrieve_data()
        cd = self.company_data
        df = cd[cd.Exchange.isin(exchanges)]
        return df.filter(items=['Symbol', 'Name', 'Sector', 'industry'])

