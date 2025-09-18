#Redis Structure

Redis stores orders, completed orders (for some time), order cancellations, and a list of open orders for each user. 

###Orders
When an order is created, it is added to the order queue in this format:



	"amount":10000,

	"ordertype": "bid",

	"instrument": "ltc_btc",

	price:".0324",

	"uid": 25

Redis will check the corresponding bid/ask table (in this case, "ltc_btc/ask") for orders that can
match the new one. Both sorted sets are in the following format (orderid, price):


	("73bc9266b5a8d3d6aa0518f955c8ec39928a426f605d3c58509a3dfcd6b85c50", .024),

	("131631c56d80d706a7f4e1398c3b3147e184fe999d52174acf1a340dfb0bab1b", .024),

	("f98eba4e516108f873e5dafbf05b63f3f9cc511531ec13568fa2ba83ac793806", .024)

If nothing is found, it will add it as is to the book. Otherwise, if it can be filled partially it will adjust the amount (on both) and add it to the book. If any portion has been filled, an entry will be added to the completed list in this format:


	"bid_currency_amount": 5000, #where LTC is the base, and BTC the quote in the 'LTC/BTC' pair

	"quote_currency_amount": 5000,

	price:".0324",


### Open Orders
Each user will have a set for open orders with a list of orderids, e.g:

[
"ad557cd0ac0cac856a87bb89235e0a1aa420faaca261916508e2463b224e46da", 
"2c4fc0430c219689b8131243587ee0065d0d4f70c25eb6cefb31e60ac2105369"
]

### Order cancellation
Order cancellation is in the same queue as actual orders, but an order cancellation hash will be in the following format:


	"old_order_id":2c4fc0430c219689b8131243587ee0065d0d4f70c25eb6cefb31e60ac2105369,

	"ordertype":"cancel"
