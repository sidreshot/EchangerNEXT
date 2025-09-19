# EchangerNEXT

EchangerNEXT is a lightweight cryptocurrency exchange prototype written in Python
and Flask. The project now targets modern Python 3 environments and provides
first-class support for JSON-RPC compatible wallets for Bitcoin, Litecoin,
Bitcoin Cash, Dash and Dogecoin.

## Features

* Responsive Bootstrap 5 web interface optimised for desktop and mobile users.
* Redis-backed limit order book with background workers for matching and deposit
  processing.
* Configurable support for the top five Bitcoin-compatible wallets via
  JSON-RPC.
* SQLite database (default) with SQLAlchemy models, ready for migration to other
  SQL backends.
* Email notifications through Flask-Mail (optional).
* Comprehensive configuration through environment variables or a `.env` file.
* Pytest-based automated test suite.

## Requirements

The application is developed and tested against Debian 13 (Trixie) with Python
3.11. Install the required system packages:

```bash
sudo apt update
sudo apt install python3 python3-venv python3-pip redis-server build-essential
```

Ensure the Redis service is running:

```bash
sudo systemctl enable --now redis-server
```

## Installation

1. Clone the repository and create a virtual environment:

   ```bash
   git clone https://github.com/sidreshot/EchangerNEXT.git
   cd EchangerNEXT
   python3 -m venv .venv
   source .venv/bin/activate
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

2. Copy the example environment file and adjust values for your deployment:

   ```bash
   cp .env.sample .env
   ```

   At a minimum, set secure RPC URLs (including credentials) for each coin you
   plan to enable and choose a strong `SECRET_KEY`.

3. Initialise the database and start the development server:

   ```bash
   flask --app run.py db
   flask --app run.py run --debug
   ```

   The site will be available at <http://127.0.0.1:5000/>.

## Running background workers

Two background processes keep the exchange state up to date:

* **Depositor** (`python -m app.depositor --interval 60`): polls RPC daemons for
  confirmed deposits and credits user balances.
* **Order worker** (`python -m app.worker`): matches orders from the Redis order
  book and writes completed trades to the SQL database.

Both commands accept `--once` to process a single iteration which is convenient
for cron jobs and testing.

## API reference

All responses are JSON encoded.

| Endpoint | Description |
| --- | --- |
| `GET /api/volume/<instrument>` | 24h volume snapshot for the trading pair. |
| `GET /api/high/<instrument>` | Highest executed price in the last 24h. |
| `GET /api/low/<instrument>` | Lowest executed price in the last 24h. |
| `GET /api/orders/<instrument>/<bid|ask>` | Snapshot of the order book side. |

Trading pair names follow the `base_quote` convention (e.g. `ltc_btc`).

## Testing

Activate the virtual environment and execute:

```bash
pytest
```

The suite uses `fakeredis` to avoid requiring a live Redis server.

## Logging

Structured console logging is configured automatically. Set the environment
variable `FLASK_ENV=production` to reduce verbosity.

## License

This project remains open source under the MIT license.
