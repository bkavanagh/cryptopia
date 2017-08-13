from concurrent import futures
from api import Cryptopia
import config

c = Cryptopia(config.CRYPTOPIA_API_KEY, config.CRYPTOPIA_API_SECRET)

markets = c.get_list_data()
for market in markets:
    print(market.last_trade)
