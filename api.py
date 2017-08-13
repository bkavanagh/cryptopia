import requests
import json
import hashlib
import time
import base64
import hmac
from functools import wraps
from urllib.parse import urljoin
from urllib.parse import quote_plus
from collections import namedtuple
from utils import camel_to_snake

DEBUG = True


class CurrencyBase:

    def __init__(self, id=None, symbol=None, status=None, status_message=None):
        self.id = id
        self.symbol = symbol
        self.status = status
        self.status_message = status_message


class Currency(CurrencyBase):

    def __init__(self, name=None,  algorithm=None, withdraw_fee=None, min_withdraw_fee=None,
                 min_base_trade=None, is_tip_enabled=None, min_tip=None, deposit_confirmations=None, listing_status=None,
                 min_withdraw=None, max_withdraw=None, **kwargs):
        self.name = name
        self.algorithm = algorithm
        self.withdraw_fee = withdraw_fee
        self.min_withdraw_fee = min_withdraw_fee
        self.min_base_trade = min_base_trade
        self.is_tip_enabled = is_tip_enabled
        self.min_tip = min_tip
        self.deposit_confirmations = deposit_confirmations

        self.listing_status = listing_status
        self.min_withdraw = min_withdraw
        self.max_withdraw = max_withdraw
        super(Currency, self).__init__(**kwargs)


class TradePair(CurrencyBase):

    def __init__(self,label=None, currency=None, base_currency=None, base_symbol=None, trade_fee=None,
                 minimum_trade=None, maximum_trade=None, minimum_base_trade=None, maximum_base_trade=None,
                 minimum_price=None, maximum_price=None, **kwargs):
        self.label = label
        self.currency = currency
        self.base_currency = base_currency
        self.base_symbol = base_symbol
        self.trade_fee = trade_fee
        self.minimum_trade = minimum_trade
        self.maximum_trade = maximum_trade
        self.minimum_base_trade = minimum_base_trade
        self.maximum_base_trade = maximum_base_trade
        self.minimum_price = minimum_price
        self.maximum_price = maximum_price
        super(TradePair, self).__init__(**kwargs)


class ListData(CurrencyBase):

    def __init__(self, trade_pair_data=None, trade_pair_id=None, currency_id=None, base_symbol=None, change=None,
                 last_trade=None, **kwargs):
        self.trade_pair_data = trade_pair_data
        self.trade_pair_id = trade_pair_id
        self.currency_id = currency_id
        self.base_symbol = base_symbol
        self.change = change
        self.last_trade = last_trade
        super(ListData, self).__init__(**kwargs)


class RequestParamsException(Exception):pass


class RequestData(object):

    def __init__(self, arg=None, params=None, headers=None, data=None):
        self.data = data
        self.params = params
        self.headers = headers
        self.arg = arg


def url(url, method='get', ret_class=None):
    def _decorator(f):
        @wraps(f)
        def _wrapper(self, *args, **kwargs):
            r = f(self, *args, **kwargs) or RequestData()
            u = self.base_url + url
            return getattr(self, method)(u, r, ret_class)
        return _wrapper
    return _decorator


class Cryptopia(object):

    public_methods = ['GetCurrencies', 'GetTradePairs', 'GetMarkets', 'GetMarket', 'GetMarketHistory', 'GetMarketOrders', 'GetMarketOrderGroups']
    private_methods = ['GetBalance', 'GetDepositAddress', 'GetOpenOrders', 'GetTradeHistory', 'GetTransactions', 'SubmitTrade', 'CancelTrade', 'SubmitTip', 'SubmitWithdraw', 'SubmitTransfer']
    base_url = 'https://www.cryptopia.co.nz/'

    def __init__(self, key, secret):
        self._key = key
        self._secret = secret

    @property
    def secret_64(self):
        return base64.b64decode(self._secret)

    @property
    def string_time(self):
        return str(time.time())

    def generate_hmac(self, signature):
        return base64.b64encode(hmac.new(self.secret_64, signature.encode('utf-8'), hashlib.sha256).digest())

    def generate_signature(self, data, request_url,  nonce):
        m = hashlib.md5()
        post_data = json.dumps(data)
        m.update(post_data.encode('utf-8'))
        content_b64 = base64.b64encode(m.digest()).decode('utf-8')
        return self._key + 'POST' + quote_plus(request_url).lower() + nonce + content_b64

    def post(self, request_url, rdata):
        data = rdata.data or {}
        nonce = self.string_time
        signature = self.generate_signature(data, request_url, nonce)
        hmac_signature = self.generate_hmac(signature)
        auth = "amx " + self._key + ":" + hmac_signature.decode('utf-8') + ":" + nonce
        headers = {'Authorization': auth, 'Content-Type': 'application/json; charset=utf-8'}
        r = requests.post(request_url, data=json.dumps(data), headers=headers)
        print(request_url, r.status_code)
        r.encoding = "utf-8-sig"
        return r.json()

    def get(self, request_url, rdata, ret_class=None):
        request_url = urljoin(request_url, rdata.arg)
        print(request_url)
        r = requests.get(request_url, params=rdata.params, headers=rdata.headers)
        try:
            ret = r.json().get('Data')
        except AttributeError:
            ret = r.json()
        if ret_class:
            yield from (ret_class(**{camel_to_snake(k): v for k, v in result.items()}) for result in ret)
        else:
            yield from ret

    @url('api/GetMarkets/', method='get', ret_class=Market)
    def get_markets(self, base_market=None, hours=None):
        return RequestData(params={'baseMarket': base_market, 'hours': hours})

    @url('api/GetMarket/', method='get')
    def get_market(self, market):
        return RequestData(arg=(str(market)))

    @url('api/GetMarketHistory/', method='get')
    def get_market_history(self, market, hours=None):
        return RequestData(arg=(str(market)), params={hours: hours or 24})

    @url('api/GetMarketOrders/', method='get')
    def get_market_orders(self, market, count=100):
        return RequestData(arg=(str(market)), params={'orderCount': count})

    @url('api/GetMarketOrderGroups/', method='get')
    def get_market_order_groups(self, *groups, count=100):
        groups = (str(x) for x in groups)
        return RequestData(arg=('-'.join(groups)), params={'orderCount': count})

    @url('api/GetCurrencies/', method='get', ret_class=Currency)
    def get_currencies(self): pass

    @url('api/GetTradePairs/', method='get')
    def get_trade_pairs(self): pass

    @url('Exchange/GetListData/', method='get', ret_class=MarketListItem)
    def get_list_data(self, t=None):
        t = t or time.time()
        return RequestData(params={'_': t})

    @url('api/GetBalance/', method='post')
    def get_balance(self, currency=None, currency_id=None):
        return RequestData(data={
            'Currency': currency,
            'CurrencyId': currency_id
        })

    @url('api/GetDepositAddress', method='post')
    def get_deposit_address(self, currency=None, currency_id=None):
        return RequestData(data={
            'Currency': currency,
            'CurrencyId': currency_id
        })

    @url('api/GetOpenOrders', method=post)
    def get_open_orders(self, market=None, trade_pair_id=None, count=100):
        return RequestData(data={
            'Market': market,
            'TradePairId': trade_pair_id,
            'Count': count
        })

    @url('api/GetTradeHistory', method='post')
    def get_trade_history(self, market=None, trade_pair_id=None, count=100):
        return RequestData(data={
            'Market': market,
            'TradePairId': trade_pair_id,
            'Count': count
        })

    @url('api/GetTransactions', method='post')
    def get_transactions(self, transaction_type='Withdraw', count=100):
        return RequestData(data={
            'Type': transaction_type,
            'Count': count
        })

    @url('api/SubmitTrade', method='post')
    def submit_trade(self, market=None, trade_pair=None, trade_type='Buy', rate=0.00000001, amount=0):
        return RequestData(data={
            'Market': market,
            'TradePairId': trade_pair,
            'Type': trade_type,
            'Rate': rate,
            'Amount': amount
        })

    @url('api/CancelTrade', method='post')
    def cancel_trade(self, trade_type='All', order_id=None):
        if not trade_type in ['All', 'Trade', 'TradePairId']:
            raise(RequestParamsException('Cancel type must be All, Trade or TradePair'))
        return RequestData(data={
            'Type': trade_type,
            'OrderId': order_id
        })

    @url('api/SubmitTip', method='post')
    def submit_tip(self, currency=None, currency_id=None, active_users=0, amount=0):
        return RequestData(data={
            'Currency': currency,
            'CurrencyId': currency_id,
            'ActiveUsers': active_users,
            'Amount': amount
        })

    @url('api/SubmitWithdraw', method='post')
    def submit_withdraw(self, currency=None, currency_id=None, address=None, payment_id=None, amount=0):
        return RequestData(data={
            'Currency': currency,
            'CurrencyId': currency_id,
            'Address': address,
            'PaymentId': payment_id,
            'Amount': amount
        })
               
    @url('api/SubmitTransfer', method='post')
    def submit_transfer(self, currency=None, currency_id=None, username=None, amount=0):
        return RequestData(data={
            'Currency': currency,
            'CurrencyId': currency_id,
            'Username': username,
            'Amount': amount
        })

if __name__ == '__main__':
    pass



