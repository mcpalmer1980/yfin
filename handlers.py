import ibx
from common import *

def random_handler(own, percent):
    if own:
        if percent < -7:
            print('heavy loss: liquidating')
            market.ib.SellAll()
        elif percent > 4:
            print('profit goal attained: liquidating')
            market.ib.SellAll()
        else:
            print('position okay: no action taken')
    else:
        print(term.blink('You own no stocks: buy 1 long, 1 short'))
        time.sleep(6)
        print(term.move_up + ('You own no stocks: buy 1 long, 1 short'))

def default_handler(own, percent):
    print('No handler for current market state: using random')
    random_handler(own, percent)

state_handlers = {
    'down': None,
    'downtrend': None,
    'random': random_handler,
    'uptrend': None,
    'up': None }

def liquidate():
    global running
    print(term.red('simulated liquidation!'))
    running = False

def launch(state, ib):
    own = False
    percent = 0

    if ib.connected:
        portfolio = market.ib.GetStocksFrame()
        if portfolio:
            own = True
            pnl = portfolio.iat[-1, -1]
            cost = portfolio.iat[-1, -2]
            percent = (pnl / cost) * 100
            print(f'profit: {percent}')
    
    handler = state_handlers.get(state, None)
    if handler:
        handler(own, percent)
    else:
        # TODO - remove this
        default_handler(own, percent)
