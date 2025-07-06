# -------------------------------------------------------------------------------------------------
#  Copyright (C) 2015-2024 Nautech Systems Pty Ltd. All rights reserved.
#  https://nautechsystems.io
#
#  Licensed under the GNU Lesser General Public License Version 3.0 (the "License");
#  You may not use this file except in compliance with the License.
#  You may obtain a copy of the License at https://www.gnu.org/licenses/lgpl-3.0.en.html
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
# -------------------------------------------------------------------------------------------------

import pandas as pd
from nautilus_trader.core.nautilus_pyo3 import LogColor
from smc_indicator import SmartMoneyConcept
from nautilus_trader.config import StrategyConfig
from nautilus_trader.model.book import OrderBook
from nautilus_trader.model.data import Bar
from nautilus_trader.model.data import BarType
from nautilus_trader.model.data import OrderBookDeltas
from nautilus_trader.model.data import QuoteTick
from nautilus_trader.model.data import TradeTick
from nautilus_trader.model.data import BarSpecification
from nautilus_trader.model.enums import AggregationSource
from nautilus_trader.model.enums import BarAggregation
from nautilus_trader.model.enums import BookType
from nautilus_trader.model.enums import PriceType
from nautilus_trader.model.identifiers import InstrumentId
from nautilus_trader.trading.strategy import Strategy


import os

from nautilus_trader.adapters.interactive_brokers.common import IB
from nautilus_trader.adapters.interactive_brokers.common import IB_VENUE
from nautilus_trader.adapters.interactive_brokers.common import IBContract
from nautilus_trader.adapters.interactive_brokers.config import DockerizedIBGatewayConfig
from nautilus_trader.adapters.interactive_brokers.config import IBMarketDataTypeEnum
from nautilus_trader.adapters.interactive_brokers.config import InteractiveBrokersDataClientConfig
from nautilus_trader.adapters.interactive_brokers.config import InteractiveBrokersExecClientConfig
from nautilus_trader.adapters.interactive_brokers.config import InteractiveBrokersInstrumentProviderConfig
from nautilus_trader.adapters.interactive_brokers.factories import InteractiveBrokersLiveDataClientFactory
from nautilus_trader.adapters.interactive_brokers.factories import InteractiveBrokersLiveExecClientFactory
from nautilus_trader.config import LiveDataEngineConfig
from nautilus_trader.config import LoggingConfig
from nautilus_trader.config import RoutingConfig
from nautilus_trader.config import TradingNodeConfig
from nautilus_trader.examples.strategies.subscribe import SubscribeStrategy
from nautilus_trader.examples.strategies.subscribe import SubscribeStrategyConfig
from nautilus_trader.live.node import TradingNode
from nautilus_trader.model.identifiers import InstrumentId


class SmartMoneyConceptStrategyConfig(StrategyConfig, frozen=True):
    """
    Configuration for ``SmartMoneyConceptStrategy`` instances.

    Parameters
    ----------
    instrument_id : InstrumentId
        The instrument ID for the strategy.

    """

    instrument_id: InstrumentId
    bar_type: BarType


class SmartMoneyConceptStrategy(Strategy):
    """
    A strategy that subscribes to bar data and apply SMC strategy

    Parameters
    ----------
    config : OrderbookImbalanceConfig
        The configuration for the instance.

    """

    def __init__(self, config: SmartMoneyConceptStrategyConfig) -> None:
        super().__init__(config)

        # Configuration
        self.instrument_id = config.instrument_id
        self.bar_type = config.bar_type

        # Create indicators
        self.smc = SmartMoneyConcept(period=5, order_block_count=5)

    def on_start(self) -> None:
        self.instrument = self.cache.instrument(self.instrument_id)
        if self.instrument is None:
            self.log.error(f"Could not find instrument for {self.instrument_id}")
            self.stop()
            return

        # Register the indicators for updating
        self.register_indicator_for_bars(self.bar_type, self.smc)

        # Get historical data
        self.request_bars(self.bar_type, start=self._clock.utc_now() - pd.Timedelta(days=1))

        # Subscribe to live data
        # self.subscribe_quote_ticks(self.instrument_id)
        self.subscribe_bars(self.bar_type)

    def on_order_book_deltas(self, deltas: OrderBookDeltas) -> None:
        if not self.book:
            self.log.error("No book being maintained")
            return

        self.book.apply_deltas(deltas)
        self.log.info(str(self.book))

    def on_order_book(self, order_book: OrderBook) -> None:
        self.book = order_book
        self.log.info(str(self.book))

    def on_trade_tick(self, tick: TradeTick) -> None:
        self.log.info(str(tick))

    def on_quote_tick(self, tick: QuoteTick) -> None:
        self.log.info(str(tick))

    def on_bar(self, bar: Bar) -> None:
        self.log.info(str(Bar.to_dict(bar)))
        self.log.info(f"Order blocks:\t{len(self.smc.get_order_blocks())}", LogColor.GREEN)
        self.log.info(f"Order blocks:\t{list(self.smc.get_order_blocks())}", LogColor.GREEN)
        # self.series.append(Bar.to_dict(bar))

    def on_stop(self) -> None:
        df = pd.DataFrame([Bar.to_dict(bar) for bar in self.smc.bars])
        df.set_index("ts_event", inplace=True)
        df.to_csv("playground/bars.csv")

        df = pd.DataFrame(
            self.smc.get_order_blocks(),
            columns=["low", "high", "ts_event", "OrderBlockType"],
        )
        df.to_csv("playground/ob.csv")
