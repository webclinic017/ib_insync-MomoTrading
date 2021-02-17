from ib_insync import *
from buckets import *
import pandas as pd
from statistics import stdev

# create dictionary of account and portfolio values for risk management
def accountAndPositions():
    acct = util.tree(ib.accountSummary())
    acctSum = {}
    for index in (20, 9, 13, 32):
        acctSum[acct[index]['tag']] = acct[index]['value']
    positions = util.tree(ib.positions())
    acctSum['Positions'] = acctPos = {}
    for index in range(len(positions)):
        acctPos[positions[index]['contract']['Option']['symbol']] = [
            positions[index]['contract']['Option']['secType'],
            positions[index]['contract']['Option']['strike'],
            positions[index]['contract']['Option']['right'],
            positions[index]['contract']['Option']['lastTradeDateOrContractMonth'],
            positions[index]['position'],
            round(positions[index]['position'] * positions[index]['avgCost'], 2)
        ]
    return acctSum

# sectorMax variable can be altered ############################################
def sectorAtCapacity(buckets_security):
    buckets_security = buckets_security
    sectorMax = 20
    sectorExposure = sectorExposureDict()
    trueOrFalse = []
    for key in sectorExposure.keys():
        if buckets_security[3] == key:
            if sectorExposure[key]['percent'] >= sectorMax:
                trueOrFalse.append(True)
        else:
            trueOrFalse.append(False)
    if True in trueOrFalse:
        return True
    else:
        return False

# riskPercentages (.01, .01, .02, .03) variables can be altered ################
def riskPercentageAllowed():
    acctValue = float(accountAndPositions()['NetLiquidation'])
    riskPercentages = {}
    riskPercentages['sma9'] = round((acctMult*acctValue) * .01, 2)
    riskPercentages['sma20'] = round((acctMult*acctValue) * .01, 2)
    riskPercentages['sma50'] = round((acctMult*acctValue) * .02, 2)
    riskPercentages['sma200'] = round((acctMult*acctValue) * .03, 2)
    return riskPercentages

# diversification limits
def sectorExposureDict():
    sectorExposure = {}
    for holding in range(len(hits)):
        for stock in range(len(BB_securities)):
            if hits[holding][0] == BB_securities[stock][0]:
                sectorExposure[BB_securities[stock][3]] = {}
    for key in sectorExposure:
        for holding in range(len(hits)):
            if key == hits[holding][2]:
                sectorExposure[key][hits[holding][0]] = hits[holding][1]
    for sector in sectorExposure.keys():
        total = 0
        for key in sectorExposure[sector].keys():
            total += sectorExposure[sector][key]
        sectorExposure[sector]['total'] = total
    # figure out whether to use netLiquidation value or (netliquidation value - unrl gains)  in risk limits
    netLiquidationValue = float(accountAndPositions()['NetLiquidation'])
    unrlPnL = float(accountAndPositions()['UnrealizedPnL'])
    acctTotal = netLiquidationValue #- unrlPnL
    for sector in sectorExposure.keys():
        percent = round((sectorExposure[sector]['total'] / acctTotal) * 100, 2)
        sectorExposure[sector]['percent'] = percent
    return sectorExposure

def stockOptionCallSelector(security, expiry):
    stock = Stock(security, 'SMART', 'USD')
    ib.qualifyContracts(stock)
    ib.reqMarketDataType(1)
    [ticker] = ib.reqTickers(stock)
    value = ticker.marketPrice()
    chains = ib.reqSecDefOptParams(stock.symbol, '', stock.secType, stock.conId)
    chain = next(c for c in chains if c.tradingClass == security and c.exchange == 'SMART')
    strikes = [strike for strike in chain.strikes
            if strike % 1 == 0
            and value - 15 < strike < value]
    #expirations = sorted(expiry for exp in chain.expirations)#[0:12] #0:1 = closest exp
    #rights = ['C']
    contracts = [Option(security, expiry, strike, 'C', 'SMART', tradingClass=security)
            # for right in rights
            #for expiration in expirations
            for strike in strikes]
    contracts = ib.qualifyContracts(*contracts)
    tickers = util.tree(ib.reqTickers(*contracts))
    # expTickers = []
    # expTickers.append(tickers[data])
    # for data in range(len(tickers)):
    #     if tickers[data]['Ticker']["contract"]["Option"]["lastTradeDateOrContractMonth"] == expiry:
    #         expTickers.append(tickers[data])
    executableOption = tickers[len(tickers)-1]
    return executableOption

def stockOptionPutSelector(security, expiry):
    stock = Stock(security, 'SMART', 'USD')
    ib.qualifyContracts(stock)
    ib.reqMarketDataType(1)
    [ticker] = ib.reqTickers(stock)
    value = ticker.marketPrice()
    chains = ib.reqSecDefOptParams(stock.symbol, '', stock.secType, stock.conId)
    chain = next(c for c in chains if c.tradingClass == security and c.exchange == 'SMART')
    strikes = [strike for strike in chain.strikes
            if strike % 1 == 0
            and value + 15 > strike > value]
    #expirations = sorted(expiry for exp in chain.expirations)#[0:12] #0:1 = closest exp
    #rights = ['C']
    contracts = [Option(security, expiry, strike, 'P', 'SMART', tradingClass=security)
            # for right in rights
            #for expiration in expirations
            for strike in strikes]
    contracts = ib.qualifyContracts(*contracts)
    tickers = util.tree(ib.reqTickers(*contracts))
    # expTickers = []
    # expTickers.append(tickers[data])
    # for data in range(len(tickers)):
    #     if tickers[data]['Ticker']["contract"]["Option"]["lastTradeDateOrContractMonth"] == expiry:
    #         expTickers.append(tickers[data])
    executableOption = tickers[0]
    return executableOption

def testExpiryAvailability(bucket, expiry, bool):
    expiryIsAvailable = []
    expiryIsNotAvailable = []
    for ticker in range(len(bucket)):
        try:
            buyOption = stockOptionCallSelector(bucket[ticker][0], expiry)
            expiryIsAvailable.append(buyOption['Ticker']['contract']['Option']['symbol'])
        except (KeyError, IndexError):
            expiryIsNotAvailable.append(bucket[ticker][0])
    if bool == True:
        return expiryIsAvailable
    elif bool == False:
        return expiryIsNotAvailable
# available = testExpiryAvailability(SMA50_securities, '20210416', True)
# notAvailable = testExpiryAvailability(SMA50_securities, '20210416', False)
# print(available)
# print(len(available))
# print(notAvailable)
# print(len(notAvailable))
# print(len(SMA50_securities))

def callBuyOrder(ticker, exp, quant):
    optionDetails = stockOptionCallSelector(ticker, exp)
    contract = Option(optionDetails['Ticker']['contract']['Option']['symbol'],
                      optionDetails['Ticker']['contract']['Option']['lastTradeDateOrContractMonth'],
                      optionDetails['Ticker']['contract']['Option']['strike'],
                      optionDetails['Ticker']['contract']['Option']['right'],
                      optionDetails['Ticker']['contract']['Option']['exchange'])
    order = MarketOrder('BUY', quant, algoStrategy='Adaptive', algoParams = [TagValue('adaptivePriority', 'Urgent')])
    trade = ib.placeOrder(contract, order)

def putBuyOrder(ticker, exp, quant):
    optionDetails = stockOptionPutSelector(ticker, exp)
    contract = Option(optionDetails['Ticker']['contract']['Option']['symbol'],
                      optionDetails['Ticker']['contract']['Option']['lastTradeDateOrContractMonth'],
                      optionDetails['Ticker']['contract']['Option']['strike'],
                      optionDetails['Ticker']['contract']['Option']['right'],
                      optionDetails['Ticker']['contract']['Option']['exchange'])
    order = MarketOrder('BUY', quant, algoStrategy='Adaptive', algoParams = [TagValue('adaptivePriority', 'Urgent')])
    trade = ib.placeOrder(contract, order)

#determine call quantity to buy given risk parameters
def callPurchaseQuantity(ticker, exp, riskBucket):
    optionDetails = stockOptionCallSelector(ticker, exp)
    capAvail = riskPercentageAllowed()[riskBucket]
    optionPrice = (((optionDetails['Ticker']['ask']) + (optionDetails['Ticker']['bid'])) / 2) * 100
    quantityToBuy = round((capAvail / optionPrice) - ((capAvail % optionPrice) / optionPrice))
    return quantityToBuy

#determine put quantity to buy given risk parameters
def putPurchaseQuantity(ticker, exp, riskBucket):
    optionDetails = stockOptionPutSelector(ticker, exp)
    capAvail = riskPercentageAllowed()[riskBucket]
    optionPrice = (((optionDetails['Ticker']['ask']) + (optionDetails['Ticker']['bid'])) / 2) * 100
    quantityToBuy = round((capAvail / optionPrice) - ((capAvail % optionPrice) / optionPrice))
    return quantityToBuy

# BEWARE!!!  if two postions with the same ticker are held errors will occur.
def sellTotalPosition(ticker):
    lastTradeDateOrContractMonth = accountAndPositions()['Positions'][ticker][3]
    strike = accountAndPositions()['Positions'][ticker][1]
    right = accountAndPositions()['Positions'][ticker][2]
    exchange = 'SMART'
    quant = accountAndPositions()['Positions'][ticker][4]
    contract = Option(ticker, lastTradeDateOrContractMonth, strike, right, exchange)
    order = MarketOrder('SELL', quant, algoStrategy='Adaptive', algoParams = [TagValue('adaptivePriority', 'Urgent')])
    trade = ib.placeOrder(contract, order)

# BEWARE!!!  if two postions with the same ticker are held errors will occur.
def sellAllPositions():
    positions = util.tree(ib.positions())
    for position in range(len(positions)):
        sellTotalPosition(positions[position]['contract']['Option']['symbol'],
                     positions[position]['position'])

#append hits list with current positions prior to initiating program
def startupHitsAppend():
    positions = util.tree(ib.positions())
    for index in range(len(positions)):
        hits.append([positions[index]['contract']['Option']['symbol'],
        round(positions[index]['position'] * positions[index]['avgCost'], 2)])
    for holding in range(len(hits)):
        for stock in range(len(BB_securities)):
            if hits[holding][0] == BB_securities[stock][0]:
                hits[holding].append(BB_securities[stock][3])

def condenseHits():
    hitsCondensed = []
    for item in range(len(hits)):
        hitsCondensed.append(hits[item][0])
    return hitsCondensed


# get daily historical bar data from IBKR api
def fetch_data(ticker, prime_exch, data_barcount):
    stock = Stock(ticker, 'SMART', 'USD', primaryExchange = prime_exch)
    bars = ib.reqHistoricalData(
        stock, endDateTime='', durationStr=data_barcount, #365days max
        barSizeSetting='1 day', whatToShow='MIDPOINT', useRTH=True)
    bars = util.tree(bars)
    return bars

# reduce bar data down to closing price for easy moving avg calculation
def extract_closing(singlestock_bardata):
    closing_prices = []
    for day in range(len(singlestock_bardata)):
        closing_prices.append((singlestock_bardata[day]['BarData']['close']))
    return closing_prices

# create desired length moving average list of values for charting
def create_masubplot(length, closing_prices):
    ma_length = length
    i = 0
    averages = {'data':[]}
    while i < len(closing_prices) - ma_length + 1:
        this_window = closing_prices[i : i + ma_length]
        window_average = round(sum(this_window) / ma_length, 2)
        averages['data'].append(window_average)
        i += 1
    return averages

# create desired upper bollinger band list of values for charting
def create_upperbb_subplot(closing_prices, period, std):
    length = period
    i = 0
    bb = {'data':[]}
    while i < len(closing_prices) - length + 1:
        this_window = closing_prices[i : i + length]
        window_bb = round((sum(this_window) / length) + (2.5 * stdev(this_window)), 2)
        bb['data'].append(window_bb)
        i += 1
    return bb

# create desired lower bollinger band list of values for charting
def create_lowerbb_subplot(closing_prices, period, std):
    length = period
    i = 0
    bb = {'data':[]}
    while i < len(closing_prices) - length + 1:
        this_window = closing_prices[i : i + length]
        window_bb = round((sum(this_window) / length) - (2.5 * stdev(this_window)), 2)
        bb['data'].append(window_bb)
        i += 1
    return bb

# algoTrader = Main Program
def algoTrader(bucket, maLength, exp, riskCap):
    try:
        for security in range(len(bucket)):
            ib.sleep(1)
            fetched_data = fetch_data(bucket[security][0], bucket[security][1], '365 D')
            closing_prices = extract_closing(fetched_data)
            sma = create_masubplot(maLength, closing_prices)
            if bucket[security][0] not in hitsCondensed:
                if (closing_prices[len(closing_prices)-1] < (bucket[security][4] * sma['data'][len(sma['data'])-1])):
                    if sectorAtCapacity(bucket[security]) == False:
                        if len(hitsCondensed) < dailyLimit:
                            hitsCondensed.append(bucket[security][0])
                            quant = callPurchaseQuantity(bucket[security][0], exp, riskCap)
                            callBuyOrder(bucket[security][0], exp, quant)
                        else:
                            if [bucket[security][0], 'Daily Limit'] not in missedHits:
                                missedHits.append([bucket[security][0], 'Daily Limit'])
                                print('\nDaily Limit Reached.')
                                print(f'''Missed: {missedHits}\n''')
                    else:
                        if [bucket[security][0], 'Max Sector Allocation'] not in missedHits:
                            missedHits.append([bucket[security][0], 'Max Sector Allocation'])
                            print('\nSector Exposure at Capacity.')
                            print(f'''Missed: {missedHits}\n''')
                else:
                    print(f'''{bucket[security][0]} not in buying range.''')
        startupHitsAppend()
        print(f'''\nSector Exposure: {sectorExposureDict()}\n''')
        print(f'''Missed Hits: {missedHits}''')
        print(f'''Hits not executed due to Error: {missedHitsDueToError}''')
        print(f'''Hits: {hitsCondensed}   <=   Limit: {dailyLimit}\n''')
    except (KeyError, IndexError):
        print(f'''\nError: {bucket[security][0]}\n''')
        missedHitsDueToError.append(bucket[security][0])





# START OF PROGRAM   START OF PROGRAM   START OF PROGRAM   START OF PROGRAM ###
hits = []
missedHits =[]
missedHitsDueToError = []
acctMult = 1

# #CHECK DAILY HITS AND DAILY LIMIT IN CASE OF LOST CONNECTION
# #LIVE LIVE LIVE LIVE LIVE LIVE LIVE LIVE LIVE LIVE LIVE LIVE LIVE LIVE LIVE
# ib = IB()
# ib.connect('127.0.0.1', 4001, clientId=2)

#paper trading (TWS)
ib = IB()
if ib.isConnected() == False:
    ib.connect('127.0.0.1', 7497, clientId=2)

# #paper trading (ibGateway)
# ib = IB()
# ib.connect('127.0.0.1', 4002, clientId=2)

startupHitsAppend()
print(f'''\nHits: {hits}\n''')
dailyLimit = len(hits)# + 5 #MUST BE ADJUSTED IF RESTARTED AFTER TRADE EXECUTION
hitsCondensed = condenseHits()
print(f'''Sector Exposure: {sectorExposureDict()}\n''')

while True:
    algoTrader(SMA9_securities, 9, '20210319', 'sma9')
    algoTrader(SMA20_securities, 20, '20210319', 'sma20')
    algoTrader(SMA50_securities_A, 50, '20210416', 'sma50')
    algoTrader(SMA50_securities_B, 50, '20210521', 'sma50')
    algoTrader(SMA50_securities_C, 50, '20210618', 'sma50')
    algoTrader(SMA200_securities, 200, '20210618', 'sma200')
