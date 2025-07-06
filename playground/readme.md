## Pre-requisite

- `pyenv`

### Installing TWS

- Install [TWS](https://www.interactivebrokers.com/campus/ibkr-api-page/twsapi-doc/#tws-download)
- Open TWS and follow [TWS Configuration For API Use](https://www.interactivebrokers.com/campus/ibkr-api-page/twsapi-doc/#tws-config-api)

## How to setup

Install [Nautilus Trader](https://nautilustrader.io/docs/latest/getting_started/installation)

```
pyenv virtualenv 3.12 nautilus
pyenv activate virtualenv
pip install python-dotenv
pip install -U "nautilus_trader[docker,ib]"
```

Create a new file in `/playground/.env`

```
PAPER_ACCOUNT_NUMBER="<Insert IB account number here>"
PAPER_PORT="7497"
```

## How to run

Log in TWS and run the following commands:

```
pyenv activate nautilus
cd playground
python connect_with_tws_paper.py
```