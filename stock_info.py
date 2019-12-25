import concurrent.futures
import threading
import requests
import pandas as pd
import ftplib
import io
import re
import time

class time_it():
    def __init__(self, desc=False):
        self.last_time = time.time()
        self.first_time = self.last_time
        self.desc = []
        self.time = []
        self.total = []
        if desc:
            self.add(desc, True)

    def add(self, desc, blank=False):
        new = time.time()
        self.desc.append(desc)
        if blank:
            self.time.append(0)
            self.total.append(0)
        else:
            self.time.append(new - self.last_time)
            self.total.append(new - self.first_time)        
        self.last_time = new

    def new(self, desc):
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
    
    #def __del__(self):
    #    print(self)
ti = time_it()


try:
    from requests_html import HTMLSession
except Exception:
    print("""Warning - Certain functionality 
             requires requests_html, which is not installed.
             
             Install using: 
             pip install requests_html
             
             After installation, you may have to restart your Python session.""")

    
base_url = "https://query1.finance.yahoo.com/v8/finance/chart/"

def build_url(ticker, start_date = None, end_date = None, interval = "1d"):
    
    if end_date is None:  
        end_seconds = int(pd.Timestamp("now").timestamp())
        
    else:
        end_seconds = int(pd.Timestamp(end_date).timestamp())
        
    if start_date is None:
        start_seconds = 7223400    
        
    else:
        start_seconds = int(pd.Timestamp(start_date).timestamp())
    
    site = base_url + ticker
    
    #"{}/v8/finance/chart/{}".format(self._base_url, self.ticker)
    
    params = {"period1": start_seconds, "period2": end_seconds,
              "interval": interval.lower(), "events": "div,splits"}
    
    return site, params


def force_float(elt):
    
    try:
        return float(elt)
    except:
        return elt


thread_local = threading.local()

def get_session():
    if not hasattr(thread_local, "session"):
        thread_local.session = requests.Session()
    return thread_local.session


def get_price(params):
    url, params = params
    session = get_session()
    with session.get(url, params=params) as response:
        try:
           data = response.json()
           ticker = data['chart']['result'][0]['meta']['symbol']
           price = data["chart"]["result"][0]["indicators"]["quote"][0]['close'][-1]
        except:
            ticker = url.rpartition('/')[2].upper()
            price = 'Not found'
        return ticker, price


def get_all_prices(tickers, workers = 10):
    end_date = pd.Timestamp.today() + pd.DateOffset(10)

    urls = []
    for tick in tickers:
        urls.append(build_url(tick, None, end_date, '1d'))


    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        return executor.map(get_price, urls)

def get_all_prices_slow(tickers):
    end_date = pd.Timestamp.today() + pd.DateOffset(10)
    urls = []
    for tick in tickers:
        urls.append(build_url(tick, None, end_date, '1d'))

    results = []
    for url in urls:
        results.append(get_price(url))
    return results


def get_data(ticker, start_date = None, end_date = None, index_as_date = True,
             interval = "1d"):
    '''Downloads historical stock price data into a pandas data frame.  Interval
       must be "1d", "1wk", or "1mo" for daily, weekly, or monthly data.
    
       @param: ticker
       @param: start_date = None
       @param: end_date = None
       @param: index_as_date = True
       @param: interval = "1d"
    '''
    
    if interval not in ("1d", "1wk", "1mo"):
        raise AssertionError("interval must be of of '1d', '1wk', or '1mo'")
    
    # build and connect to URL
    ti.add('\n' + ticker, True)
    site, params = build_url(ticker, start_date, end_date, interval)
    ti.add('url built')
    resp = requests.get(site, params = params)
    ti.add('request response')
    
    if not resp.ok:
        raise AssertionError(resp.json())
        
    
    # get JSON response
    data = resp.json()
    # get open / high / low / close data
    frame = pd.DataFrame(data["chart"]["result"][0]["indicators"]["quote"][0])
    # add in adjclose
    frame["adjclose"] = data["chart"]["result"][0]["indicators"]["adjclose"][0]["adjclose"]
    # get the date info
    temp_time = data["chart"]["result"][0]["timestamp"]
    frame.index = pd.to_datetime(temp_time, unit = "s")
    frame.index = frame.index.map(lambda dt: dt.floor("d"))
    frame = frame[["open", "high", "low", "close", "adjclose", "volume"]]
    frame['ticker'] = ticker.upper()
    
    if not index_as_date:  
        frame = frame.reset_index()
        frame.rename(columns = {"index": "date"}, inplace = True)
    ti.add('processed')
    return frame



def tickers_sp500():
    '''Downloads list of tickers currently listed in the S&P 500 '''
    # get list of all S&P 500 stocks
    sp500 = pd.read_html("https://en.wikipedia.org/wiki/List_of_S%26P_500_companies")[0]
    sp_tickers = sorted(sp500.Symbol.tolist())
    
    return sp_tickers


def tickers_nasdaq():
    
    '''Downloads list of tickers currently listed in the NASDAQ'''
    
    ftp = ftplib.FTP("ftp.nasdaqtrader.com")
    ftp.login()
    ftp.cwd("SymbolDirectory")
    
    r = io.BytesIO()
    ftp.retrbinary('RETR nasdaqlisted.txt', r.write)
    
    info = r.getvalue().decode()
    splits = info.split("|")
    
    tickers = [x for x in splits if "N\r\n" in x]
    tickers = [x.strip("N\r\n") for x in tickers if 'File' not in x]
    
    tickers = sorted(list(set(tickers)))
    
    ftp.close()    

    return tickers
    
    

def tickers_other():
    '''Downloads list of tickers currently listed in the "otherlisted.txt"
       file on "ftp.nasdaqtrader.com" '''
    ftp = ftplib.FTP("ftp.nasdaqtrader.com")
    ftp.login()
    ftp.cwd("SymbolDirectory")
    
    r = io.BytesIO()
    ftp.retrbinary('RETR otherlisted.txt', r.write)
    
    info = r.getvalue().decode()
    splits = info.split("|")
    
    tickers = [x for x in splits if "N\r\n" in x]
    tickers = [x.strip("N\r\n") for x in tickers]
    tickers = [x.split("\r\n") for x in tickers]
    tickers = [sublist for outerlist in tickers for sublist in outerlist]
    
    ftp.close()    

    return tickers
    
    
def tickers_dow():
    
    '''Downloads list of currently traded tickers on the Dow'''

    site = "https://finance.yahoo.com/quote/%5EDJI/components?p=%5EDJI"
    
    table = pd.read_html(site)[0]

    dow_tickers = sorted(table['Symbol'].tolist())
    
    return dow_tickers    
    

def get_quote_table(ticker , dict_result = True): 
    
    '''Scrapes data elements found on Yahoo Finance's quote page 
       of input ticker
    
       @param: ticker
       @param: dict_result = True
    '''

    site = "https://finance.yahoo.com/quote/" + ticker + "?p=" + ticker
    
    tables = pd.read_html(site)

    data = tables[0].append(tables[1])

    data.columns = ["attribute" , "value"]

    price_etc = [elt for elt in tables if elt.iloc[0][0] == "Previous Close"][0]
    price_etc.columns = data.columns.copy()
    
    data = data.append(price_etc)
    
    quote_price = pd.DataFrame(["Quote Price", get_live_price(ticker)]).transpose()
    quote_price.columns = data.columns.copy()
    
    data = data.append(quote_price)
    
    data = data.sort_values("attribute")
    
    data = data.drop_duplicates().reset_index(drop = True)
    
    data["value"] = data.value.map(force_float)

    if dict_result:
        
        result = {key : val for key,val in zip(data.attribute , data.value)}
        return result
        
    return data    
    
    

def get_stats(ticker):
    
    '''Scrapes information from the statistics tab on Yahoo Finance 
       for an input ticker 
    
       @param: ticker
    '''

    stats_site = "https://finance.yahoo.com/quote/" + ticker + \
                 "/key-statistics?p=" + ticker
    

    tables = pd.read_html(stats_site)
    
    
    table = tables[0]
    for elt in tables[1:]:
        table = table.append(elt)

    table.columns = ["Attribute" , "Value"]
    
    table = table.reset_index(drop = True)
    
    return table



def _parse_table(url):
    
    session = HTMLSession()
    r = session.get(url)
    
    rows = r.html.find("div[data-test='fin-row']")
    
    info = [row.text.split("\n") for row in rows]
    clean = [[inner.replace(",", "") for inner in outer] for outer in info]
    

    indexes = [[ix for ix,elt in enumerate(row) if re.search("[a-z]",elt)] for row in clean]

    fixed = []
    for ix_list,nums in zip(indexes, clean):
        if len(ix_list) == 1:
            fixed.append(nums)
        else:   
            actual_ix = ix_list[1:]
            
            to_add = [nums[actual_ix[i]:actual_ix[i+1]] for 
                      i in range(len(actual_ix) - 1)]
            
            #for ix in range(len(to_add)):
            #    to_add[ix][0] = nums[0] + "-" + to_add[ix][0]        
            
            fixed.extend(to_add)
    
    
    table = pd.DataFrame(fixed).drop_duplicates().reset_index(drop = True)

    headers = [span.text for span in r.html.find("div[class='D(tbhg)'] span")]

    table.columns = headers
    

    session.close()
    
    return table


        
def get_income_statement(ticker):
    
    '''Scrape income statement from Yahoo Finance for a given ticker
    
       @param: ticker
    '''
    
    income_site = "https://finance.yahoo.com/quote/" + ticker + \
            "/financials?p=" + ticker


    table = _parse_table(income_site)      
        
    try:
        names = table.Breakdown.tolist()
        names[names.index("Basic")] = "Reported EPS - Basic"
        names[names.index("Diluted")] = "Reported EPS - Diluted"
        
        names[names.index("Basic")] = "Weighted Average Shares Outstanding - Basic"
        names[names.index("Diluted")] = "Weighted Average Shares Outstanding - Diluted"
        
        table["Breakdown"] = names
        
    except Exception:
        pass
    
    return table
    

def get_balance_sheet(ticker):
    
    '''Scrapes balance sheet from Yahoo Finance for an input ticker 
    
       @param: ticker
    '''    
    
    balance_sheet_site = "https://finance.yahoo.com/quote/" + ticker + \
                         "/balance-sheet?p=" + ticker
    

    return _parse_table(balance_sheet_site)          
        

def get_cash_flow(ticker):
    
    '''Scrapes the cash flow statement from Yahoo Finance for an input ticker 
    
       @param: ticker
    '''
    
    cash_flow_site = "https://finance.yahoo.com/quote/" + \
            ticker + "/cash-flow?p=" + ticker
    
    
    return _parse_table(cash_flow_site)          
    

def get_holders(ticker, match=None):
    
    '''Scrapes the Holders page from Yahoo Finance for an input ticker 
    
       @param: ticker
    '''    
    
    holders_site = "https://finance.yahoo.com/quote/" + \
                    ticker + "/holders?p=" + ticker
    
        
    tables = pd.read_html(holders_site , header = 0)

    return tables

    
       
    table_names = ["Major Holders" , "Direct Holders (Forms 3 and 4)" ,
                   "Top Institutional Holders" , "Top Mutual Fund Holders"]
     
    
    table_mapper = {key : val for key,val in zip(table_names , tables)}
                   
                   
    return table_mapper       

def get_analysts_info(ticker):
    
    '''Scrapes the Analysts page from Yahoo Finance for an input ticker 
    
       @param: ticker
    '''    
    
    
    analysts_site = "https://finance.yahoo.com/quote/" + ticker + \
                     "/analysts?p=" + ticker
    
    tables = pd.read_html(analysts_site , header = 0)
    
    table_names = [table.columns[0] for table in tables]

    table_mapper = {key : val for key , val in zip(table_names , tables)}
    

    return table_mapper
        

def get_live_price(ticker):
    
    '''Gets the live price of input ticker
    
       @param: ticker
    '''    

    df = get_data(ticker, end_date = pd.Timestamp.today() + pd.DateOffset(10))   
    return df.close[-1]
    
    
def _raw_get_daily_info(site):
       
    session = HTMLSession()
    
    resp = session.get(site)
    
    tables = pd.read_html(resp.html.raw_html)  
    
    df = tables[0].copy()
    
    df.columns = tables[0].columns
    
    del df["52 Week Range"]
    
    df["% Change"] = df["% Change"].map(lambda x: float(x.strip("%")))
     

 #   fields_to_change = [x for x in df.columns.tolist() if "Vol" in x \
 #                       or x == "Market Cap"]
    fields_to_change = [x for x in df.columns.tolist() if "Vol" in x]
    
    for field in fields_to_change:
        
        if type(df[field][0]) == str:
            df[field] = df[field].str.strip("B").map(force_float)
            df[field] = df[field].map(lambda x: x if type(x) == str
                                                else x * 1000000000)
            
            df[field] = df[field].map(lambda x: x if type(x) == float else
                                    force_float(x.strip("M")) * 1000000)   
    

    session.close()
    
    return df
    

def get_day_most_active():
    
    return _raw_get_daily_info("https://finance.yahoo.com/most-active?offset=0&count=100")

def get_day_gainers():
    
    return _raw_get_daily_info("https://finance.yahoo.com/gainers?offset=0&count=100")

def get_day_losers():
    
    return _raw_get_daily_info("https://finance.yahoo.com/losers?offset=0&count=100")


    

def get_top_crypto():
    
    '''Gets the top 100 Cryptocurrencies by Market Cap'''      

    session = HTMLSession()
    
    resp = session.get("https://finance.yahoo.com/cryptocurrencies?offset=0&count=100")
    
    tables = pd.read_html(resp.html.raw_html)               
                    
    df = tables[0].copy()

    
    df["% Change"] = df["% Change"].map(lambda x: float(x.strip("%").\
                                                          strip("+").\
                                                          replace(",", "")))
    del df["52 Week Range"]
    del df["1 Day Chart"]
    
    fields_to_change = [x for x in df.columns.tolist() if "Volume" in x \
                        or x == "Market Cap" or x == "Circulating Supply"]
    
    for field in fields_to_change:
        
        if type(df[field][0]) == str:
            df[field] = df[field].str.strip("B").map(force_float)
            df[field] = df[field].map(lambda x: x if type(x) == str 
                                                else x * 1000000000)
            
            df[field] = df[field].map(lambda x: x if type(x) == float else
                                    force_float(x.strip("M")) * 1000000)
            
            
    session.close()        
                
    return df
                    
        
        
        
        
        
