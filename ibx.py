#from ib_insync import *
from common import *
import ib_insync as ibi


'''
phage7777
tmux2KUP
'''


class ibx():
    def __init__(self, port=7000, _id=100, allow_error=False, **params):
        print('ibx loaded from ' + params.get('mess', "nowhere"))
        self.ib = ibi.IB()
        self.connected = False
        try:
            self.ib.connect('127.0.0.1', port, _id)
            self.ib.reqMarketDataType(3)
            self.connected=True
            print('connected to ib at {}'.format(self.ib.reqCurrentTime()))

        except:
            message = '\n'.join((
                    'Failed connecting to Interactive Brokers',
                    'Make sure Trader Workstation or the IB Gateway is logged in and running',
                    'Make sure that the API is enabled and set to port {} and id {}'.format(port, _id)))
            if not allow_error:
                print(message)
                import sys
                sys.exit()

        self.currency = params.get('currency', 'USD')
        self.trades = []

    def __del__(self):
        if self.connected:
            print('disconnected from ib at {}'.format(self.ib.reqCurrentTime()))
            self.ib.disconnect()
    
    def __getitem__(self, ticker):
        return self.GetShares(ticker)

    def Buy(self, ticker, amount, limit=None):
        print('buying {} shares of {}'.format(amount, ticker))
        contract = ibi.Stock(ticker, 'SMART', self.currency)
        self.ib.qualifyContracts(contract)
        if limit:
            order = ibi.order.LimitOrder('BUY', amount, limit)
        else:
            order = ibi.order.MarketOrder('BUY', amount)
        trade = self.ib.placeOrder(contract, order)
        self.trades.append(trade)
        return trade

    def GetPrice(self, ticker):
        contract = self.ib.qualifyContracts(ibi.Stock(ticker, 'SMART', 'USD'))
        r = self.ib.reqMktData(*contract)
        for i in range(100):
            if r.last == r.last:
                print('found price after {} tries'.format(i))
                price = r.last
                break
            self.ib.sleep(.1)
        else:
            print('using close price')
            price = r.close
        return price

    def GetShares(self, ticker):
        for position in self.ib.positions():
            if position.contract.symbol == ticker.upper():
                return position.position
        else:
            return 0
    
    def GetStocks(self):
        stocks = {}
        for position in self.ib.positions():
            stocks[position.contract.symbol] = position.position
        return stocks

    def GetStocksFrame(self):
        stocks = []


        for position in self.ib.positions():
            ticker = position.contract.symbol
            price = self.GetPrice(ticker)
            stocks.append({
                    'stock': ticker,
                    'shares': position.position,
                    'cost': position.avgCost,
                    'current': price,
                    'difference': price - position.avgCost,
                    'value': price * position.position,
                    'profit': (position.position * price) - (position.position * position.avgCost) })
        df = pd.DataFrame(columns=[
                'stock',
                'shares',
                'cost',
                'current',
                'difference' ,
                'value',
                'profit' ])
        df = df.append(stocks)
        totals = df.sum()
        totals['stock'] = 'total'
        df = df.append(totals, ignore_index=True)
        return df

    def GetStocksFrame(self):
        stocks = []

        for position in self.ib.portfolio():
            ticker = position.contract.symbol
            stocks.append({
                    'stock': ticker,
                    'shares': position.position,
                    'cost': position.averageCost,
                    'current': position.marketPrice,
                    'value': position.marketValue,
                    'profit': position.unrealizedPNL })
        df = pd.DataFrame(columns=[
                'stock',
                'shares',
                'cost',
                'current',
                'value',
                'profit' ])
        df = df.append(stocks)
        totals = df.sum()
        totals['stock'] = 'total'
        df = df.append(totals, ignore_index=True)
        return df


    def GetPrices(self, ticks = None):
        import classes
        if not ticks:
            td = TickerData()
            ticks = td[td.get_name(False)]
        start_time = time.time()
        contracts = []
        for tick in ticks:
            contracts.append(ibi.Stock(tick, 'SMART', 'USD'))
        self.ib.qualifyContracts(*contracts)
        prices = self.ib.reqTickers(*contracts)
        elapsed = time.time() - start_time
        print(prices)
        print(elapsed)


    def Sell(self, ticker=None, amount=None):
        amount = amount or self.GetShares(ticker)
        if not amount:
            print('have no shares of {} to sell'.format(ticker))
            return None
        print('selling {} shares of {}'.format(amount, ticker))
        contract = ibi.Stock(ticker, 'SMART', self.currency)
        self.ib.qualifyContracts(contract)
        order = ibi.order.MarketOrder('SELL', amount)
        trade = self.ib.placeOrder(contract, order)
        return trade
    def SellAll(self):
        tickers = self.GetStocks().keys()
        for ticker in tickers:
            self.Sell(ticker)

    def Verify(self, message='Are you sure?'):
        questions = [{
            'type': 'confirm',
            'message': message,
            'name': 'confirm',
            'default': True } ]
        return prompt(questions)['confirm']
        
    
@click.group()
def main():
    """
    Simple CLI for buying and selling using the IB API by Christopher Palmieri

    use ibx COMMAND --help for details about a sub-command
    """
    global ib
    ib = ibx()

@main.command()
@click.argument('ticker')
@click.argument('amount')
@click.option('--yes', '-y', is_flag=True, help='verify purchase without prompt')
def buy(ticker, amount, yes):
    """Buy specified number shares from given stock ticker"""
    message = 'Buy {} shares of {}'.format(amount, ticker)
    if yes or ib.Verify(message):
        ib.Buy(ticker.upper(), amount)
        ib.ib.sleep(1)
        print(ib.GetStocks())

@main.command()
@click.argument('ticker')
def price(ticker):
    """Retrieve price from IB"""
    print(ib.GetPrice(ticker))

@main.command()
@click.argument('ticker', required =False, default=None)
@click.argument('amount', required=False, default=None)
@click.option('--yes', '-y', is_flag=True, help='verify purchase without prompt')
def sell(ticker=None, amount=None, yes=False):
    """Sell specified number shares from given stock ticker (def=All)"""
    message = 'Buy {} shares of {}'.format(amount, ticker)

    if not ticker:
        if ib.Verify('Sell all stocks?'):
            ib.SellAll()
    else:
        s = str(amount) if amount else 'all'
        if yes or ib.Verify('Sell {} shares of {}'.format(s, ticker)):
            ib.Sell(ticker, amount)
            print(ib.GetStocks())

"""
@main.command()
def stocks():
    '''List all stocks owned'''
    stocks = ib.GetStocks()
    if not stocks:
        print('no stocks to list!')
        return
    for stock in stocks:
        print('{}: {}'.format(stock, stocks[stock]))
"""

@main.command()
def stocks():
    '''List all stocks owned'''
    df = ib.GetStocksFrame()
    pnl = df.iat[-1, -1]
    cost = df.iat[-1, -2]
    print(df)
    print(f"profit: {pnl}\ncost: {cost}\n{(pnl/cost)*100:0.1f}%")

@main.command()
def start():
    print(get_info('aapl', 'previous'))



def get_info(ticker, item):
    'Get info from stock ticker'
    results = yfs.get_stats(ticker)
    return results[results['Attribute'].str.contains(filter, na=False, case=False) ]



if __name__ == '__main__':
    main()