# Database schema overview

The modernised schema is intentionally small and easy to migrate. All tables are
managed through SQLAlchemy models located in `app/models.py`.

## users

| column | type | notes |
| --- | --- | --- |
| id | INTEGER | Primary key |
| username | VARCHAR(80) | Unique username |
| email | VARCHAR(255) | Unique email address |
| password_hash | VARCHAR(255) | Werkzeug compatible password hash |
| is_active | BOOLEAN | Flag used for future moderation flows |
| is_admin | BOOLEAN | Reserved for administrative users |
| created_at / updated_at | DATETIME | Timestamps |

## wallet_balances

Stores balances in the smallest currency unit (satoshis, litoshis, etc.).

| column | type | notes |
| --- | --- | --- |
| id | INTEGER | Primary key |
| user_id | INTEGER | Foreign key to `users.id` |
| currency | VARCHAR(10) | ISO-style ticker symbol |
| balance | BIGINT | Amount in smallest unit |
| created_at / updated_at | DATETIME | Timestamps |

The combination of `(user_id, currency)` is unique.

## wallet_addresses

| column | type | notes |
| --- | --- | --- |
| id | INTEGER | Primary key |
| user_id | INTEGER | Foreign key to `users.id` |
| currency | VARCHAR(10) | Currency code |
| address | VARCHAR(128) | Wallet address assigned to the user |
| label | VARCHAR(64) | Optional user label |
| created_at / updated_at | DATETIME | Timestamps |

## completed_orders

Executed trades, deposits and withdrawals are written to this table.

| column | type | notes |
| --- | --- | --- |
| id | INTEGER | Primary key |
| user_id | INTEGER | Foreign key to `users.id` |
| instrument | VARCHAR(15) | Trading pair in `base_quote` form |
| side | VARCHAR(4) | `buy`, `sell`, `DEPOSIT`, `WITHDRAW` |
| base_currency | VARCHAR(10) | Base side of the trade |
| quote_currency | VARCHAR(10) | Quote side |
| amount | BIGINT | Amount in base currency units |
| price | NUMERIC(18, 8) | Executed price |
| is_deposit | BOOLEAN | Deposit flag |
| is_withdrawal | BOOLEAN | Withdrawal flag |
| withdrawal_address | VARCHAR(128) | Destination address for withdrawals |
| transaction_id | VARCHAR(128) | RPC transaction identifier |
| created_at / updated_at | DATETIME | Timestamps |
