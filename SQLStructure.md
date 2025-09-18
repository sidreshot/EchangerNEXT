#SQL Structure

The SQL database stores permanent information such as user details, deposit addresses, and transaction history. 

### Users
The user table is self explanatory, with just basic user details. (See models.py)

### Address
The Address table stores rows each containing a cryptocurrency name (ticker name) + address and a user ID. 

### CompletedOrders
The CompletedOrders table is the largest, containing information for completed orders within the exchange, deposits, and withdrawals. 
Explanation of columns:

- currency_pair: currency1_currency2 format e.g. "ltc_btc"
- active: deprecated
- completed: deprecated
- order_type = bid, ask, deposit, or withdrawal
- price: if applicable, not on deposits or withdrawals
- user: userid
- withdrawal_complete: if the withdrawal has been paid out by the withdraw/deposit daemon
- withdrawal_address
- transaction_id: blockchain txid for withdrawals and deposits
- base_currency: first currency in trade pair
- quote_currency: second currency in trade pair
