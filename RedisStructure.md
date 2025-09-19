# Redis data layout

Redis stores the in-memory order book and pending operations. All keys are plain
strings and values are encoded as hashes or sorted sets.

## Sorted sets

| key pattern | description |
| --- | --- |
| `<instrument>/bid` | Open bid orders scored by price (highest price preferred). |
| `<instrument>/ask` | Open ask orders scored by price (lowest price preferred). |
| `<instrument>/completed` | Recently executed trades for public statistics. |

## Hashes

Each order is stored as a hash keyed by the generated order identifier. The hash
contains:

| field | description |
| --- | --- |
| `instrument` | Trading pair name (`ltc_btc`, etc.). |
| `ordertype` | `buy`, `sell` or `cancel`. |
| `amount` | Amount in base currency units (integer). |
| `uid` | User ID owning the order. |
| `price` | Limit price stored as a string. |
| `old_order_id` | Present only for cancellation entries. |

The cancellation entries are enqueued with the `cancel:<order>` identifier and
remove state from both Redis and SQL.

## Queues

| key | description |
| --- | --- |
| `order_queue` | List processed by `app.worker` to match and cancel orders. |

## Sets

| key pattern | description |
| --- | --- |
| `<user_id>/orders` | Tracks active order IDs for the user. |

All Redis operations use decoded strings which keeps the system compatible with
Python 3 runtimes.
