'stock trading algorithms for ibx project'

import ibx
from common import *
import market

def random_handler(stocks, sectors):
    'example random algo'

    # finish function is only called if the algo is chosen
    def finish(portfolio, prev_state):
        print('random algo selected')
        for ticker, position in portfolio.iterrows():
            if position.pnl < -7:
                print(f'heavy loss: liquidating {ticker}')
                #market.ib.Sell(ticker)
            elif position.pnl > 4:
                print(f'profit goal attained: liquidating {ticker}')
                #market.ib.Sell(ticker)
            else:
                print(f'position okay: no action taken for {ticker}')
    
    score = 0
    pslope = sectors.at['Total', '%pslope']
    if pslope >= 45 and pslope <= 65:
        score = 1
    print(f'random score: {score}')
    return score, finish

def up_handler(stocks, sectors):
    def finish(portfolio, prev_state):
        print('up algo selected')
        for ticker, position in portfolio.iterrows():
            if position.pnl < -7:
                print(f'heavy loss: liquidating {ticker}')
                #market.ib.Sell(ticker)
            elif position.pnl > 4:
                print(f'profit goal attained: liquidating {ticker}')
                #market.ib.Sell(ticker)
            else:
                print(f'position okay: no action taken for {ticker}')

    score = 0
    pslope = sectors.at['Total', '%pslope']
    if pslope > 65:
        score = 1
    print(f'up score: {score}')
    return score, finish

def down_handler(stocks, sectors):
    def finish(portfolio, prev_state):
        print('down algo selected')
        for ticker, position in portfolio.iterrows():
            if position.pnl < -7:
                print(f'heavy loss: liquidating {ticker}')
                #market.ib.Sell(ticker)
            elif position.pnl > 4:
                print(f'profit goal attained: liquidating {ticker}')
                #market.ib.Sell(ticker)
            else:
                print(f'position okay: no action taken for {ticker}')
    
    score = 0
    pslope = sectors.at['Total', '%pslope']
    if pslope < 65:
        score = 1
    print(f'down score: {score}')
    return score, finish

def stupid_handler(stocks, sectors):
    def finish(portfolio, prev_state):
        print('stupid algo selected')
        for ticker, position in portfolio.iterrows():
            if position.pnl < -7:
                print(f'heavy loss: keeping {ticker} anyway')
                #market.ib.Sell(ticker)
            elif position.pnl > 4:
                print(f'profit goal attained: liquidating {ticker}')
                #market.ib.Sell(ticker)
            else:
                print(f'position okay: no action taken for {ticker}')
    
    score = 0.5
    print(f'stupid score: {score}')
    return score, finish


algos = {
    'random': random_handler,
    'up': up_handler,
    'down': down_handler,
    'stupid': stupid_handler }

def launch(stocks, sectors):
    'score each algo and run the highest scored algo if score > 0'
    results = []
    print(f'\nPrevious market state: {launch.prev_state}')
    for algo in algos:
        # append a tuple for each algo: ( score, function )
        results.append( algos[algo](stocks, sectors) + (algo,) )
    
    score, func, name = sorted(results, key=lambda x: x[0])[-1] # get the hightest scored tuple
    if score > 0: # make sure score > 0
        portfolio = ib.GetPortfolio(False) 
        func(portfolio, launch.prev_state) # finish the algo by calling function
        launch.prev_state = name
launch.prev_state = None


