## Pre-requisite

- `python3 -m venv venv`

### [optional] Installing TWS

- Install [TWS](https://www.interactivebrokers.com/campus/ibkr-api-page/twsapi-doc/#tws-download)
- Open TWS and follow [TWS Configuration For API Use](https://www.interactivebrokers.com/campus/ibkr-api-page/twsapi-doc/#tws-config-api)

## How to setup

Install [Nautilus Trader](https://nautilustrader.io/docs/latest/getting_started/installation)

```
source venv/bin/activate 
pip install python-dotenv
pip install -U "nautilus_trader[docker,ib]"
```

Setup IB account info in `.env`

```
TWS_USERNAME=huang7494
TWS_PASSWORD=jjL@10920
ACCOUNT_NUMBER=DU979331
```

## How to run

Run the following commands:

```
cd playground
python connect_with_tws_paper.py
```
