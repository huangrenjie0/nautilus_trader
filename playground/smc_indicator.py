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

from itertools import islice
from time import localtime, strftime
from typing import List
from enum import Enum
from typing import Deque

from numpy import double
from nautilus_trader.core.correctness import PyCondition
from nautilus_trader.indicators.base.indicator import Indicator
from nautilus_trader.model.data import Bar
from nautilus_trader.model.data import QuoteTick
from nautilus_trader.model.data import TradeTick
from collections import deque
from nautilus_trader.common.component import init_logging
from nautilus_trader.common.component import Logger
from nautilus_trader.common.enums import LogColor
from nautilus_trader.indicators.atr import AverageTrueRange
from nautilus_trader.indicators.average.moving_average import MovingAverageType


#####################
# Helper Functions
#####################
def _get_hh_ll(bars: List[Bar]):
    hh = 0.0
    ll = 9999999999.0
    for bar in bars:
        hh = max(bar.high.as_double(), hh)
        ll = min(bar.low.as_double(), ll)
    return (hh, ll)

def _is_bar_valid_for_ob(bar: Bar, atr: double):
    return (bar.high.as_double() - bar.low.as_double()) < 2.0 * atr


def to_local_time(ts: int):
    return strftime("%Y-%m-%d %H:%M:%S", localtime(ts / 1000000000.0))


#####################
# Helper Types
#####################
class SwingType(Enum):
    LOW = 0
    HIGH = 1


class OrderBlockType(Enum):
    BUY = 0
    SELL = 1

    def __str__(self):
        return "BUY" if self == OrderBlockType.BUY else "SELL"


class Swing:
    def __init__(self, x: int, bar: Bar):
        self.x = x
        self.bar = bar
        self.is_valid = False

    def __str__(self) -> str:
        return f"x: {self.x}\tts: {to_local_time(self.bar.ts_event) if self.bar is not None else "None"}\tis_valid: {self.is_valid}"


#####################
# Main
#####################
class SmartMoneyConcept(Indicator):
    """
    SMC Indicator

    Parameters
    ----------
    period : int
        The rolling window period for the swing detection (> 0).
    order_block_count : int
        The maximum number of recent order blocks to show. Older ones will be deleted.
    """

    def __init__(self, period: int, order_block_count: int):
        PyCondition.positive_int(period, "period")
        PyCondition.positive_int(order_block_count, "order_block_count")
        super().__init__(params=[period, order_block_count])

        # Init logger
        self.log = Logger("smc_indicator")

        # Configuration
        self.period = period
        self.order_block_count = order_block_count

        # ATR Indicator
        self._atr = AverageTrueRange(200)

        # States
        self.bars = []
        self.atrs = []
        self.curr_swing_type = SwingType.LOW
        self.prev_swing_type = SwingType.LOW
        self.swing_high = Swing(0, None)
        self.swing_low = Swing(0, None)
        # Order blocks
        self._ob = deque()

    def get_order_blocks(self):
        '''
        Return only the most recent {order_block_count} of order blocks
        Order block is a list of (low, high, ts_event, OrderBlockType) ordered by ts
        '''
        return list(self._ob)
        # return list(islice(self._ob, max(0, len(self._ob) - self.order_block_count), len(self._ob)))
        

    def handle_bar(self, bar: Bar):
        """
        Update the indicator with the given bar.

        Parameters
        ----------
        bar : Bar
            The update bar to handle.

        """
        PyCondition.not_none(bar, "bar")
        self.log.debug(f"Handling bar data in SMC indicator: {str(bar)}", LogColor.BLUE)

        # Update ATR
        self._atr.update_raw(bar.high.as_double(), bar.low.as_double(), bar.close.as_double())

        # Update states
        self.bars.append(bar)
        self.atrs.append(self._atr.value)
        self.prev_swing_type = self.curr_swing_type

        if self.initialized:

            # Find sliding window's max and min
            hh, ll = _get_hh_ll(self.bars[-self.period :])
            # Candidate for swing high/low is the bar before the sliding window
            candidate_bar = self.bars[-self.period - 1]

            # Detect current swing type
            if candidate_bar.high.as_double() > hh:
                self.curr_swing_type = SwingType.LOW
            elif candidate_bar.low.as_double() < ll:
                self.curr_swing_type = SwingType.HIGH
            else:
                # No change in swing type
                self.curr_swing_type = self.prev_swing_type

            # Only update swing high/low when swing type changes
            if self.prev_swing_type == SwingType.HIGH and self.curr_swing_type == SwingType.LOW:
                # New swing high detected
                #  *
                #    |
                #      |
                #        |  
                #          |  
                self.swing_high.x = len(self.bars) - self.period - 1
                self.swing_high.bar = candidate_bar
                self.swing_high.is_valid = True

            if self.prev_swing_type == SwingType.LOW and self.curr_swing_type == SwingType.HIGH:
                # New swing low detected
                #          |  
                #        |  
                #      |
                #    |
                #  *
                self.swing_low.x = len(self.bars) - self.period - 1
                self.swing_low.bar = candidate_bar
                self.swing_low.is_valid = True

            if self.swing_high.is_valid:
                # Check if current close crossover the previous swing high
                if bar.close.as_double() > self.swing_high.bar.high.as_double():
                    min_low = 9999999999.0
                    idx = 1

                    for i in range(self.swing_high.x + 1, len(self.bars) - 1):
                        if _is_bar_valid_for_ob(self.bars[i], self.atrs[i]):
                            low = self.bars[i].low.as_double()
                            min_low = min(min_low, low)
                            idx = i if min_low == low else idx
                    # Add buy order blocks
                    self._ob.append((self.bars[idx].low.as_double(), self.bars[idx].high.as_double(), self.bars[idx].ts_event, OrderBlockType.BUY))
                    self.swing_high.is_valid = False

            if self.swing_low.is_valid:
                # Check if current close crossunder the previous swing low
                if bar.close.as_double() < self.swing_low.bar.low.as_double():
                    max_high = 0.0
                    idx = 1

                    for i in range(self.swing_low.x + 1, len(self.bars) - 1):
                        if _is_bar_valid_for_ob(self.bars[i], self.atrs[i]):
                            high = self.bars[i].high.as_double()
                            max_high = max(max_high, high)
                            idx = i if max_high == high else idx
                    # Add sell order blocks
                    self._ob.append((self.bars[idx].low.as_double(), self.bars[idx].high.as_double(), self.bars[idx].ts_event, OrderBlockType.SELL))
                    self.swing_low.is_valid = False

            # Delete order blocks box coordinates if top/bottom is broken
            n = len(self._ob)
            for _ in range(n):
                l, h, ts, type = self._ob.popleft()
                if bar.close.as_double() < l and type == OrderBlockType.BUY:
                    # Delete the order block
                    continue
                elif bar.close.as_double() > h and type == OrderBlockType.SELL:
                    # Delete the order block
                    continue
                self._ob.append((l,h,ts,type))

        # Purge oldest order block if needed
        # Note: Store double in case some order blocks are broken and deleted
        while len(self._ob) > self.order_block_count * 2:
            self._ob.popleft()

        # Initialization logic
        if not self.initialized:
            self._set_has_inputs(True)
            if len(self.bars) >= self.period:
                self._set_initialized(True)
            if self._atr.initialized:
                self._set_initialized(True)

        self.log.debug(f"ATR:\t{self._atr.value}")
        self.log.info(f"Swing High:\t{self.swing_high}")
        self.log.info(f"Swing Low:\t{self.swing_low}")
        self.log.info(f"Order blocks: {len(self._ob)}", LogColor.CYAN)
        self.log.info(f"Order blocks: {list(self._ob)}", LogColor.CYAN)

    def _reset(self):
        # Override this method to reset stateful values introduced in the class.
        # This method will be called by the base when `.reset()` is called.
        self.bars.clear()
        self.curr_swing_type = SwingType.LOW
        self.prev_swing_type = SwingType.LOW
        self.swing_high = Swing(0, None)
        self.swing_low = Swing(0, None)
        self._ob.clear()

        # Reset ATR indicator
        self._atr.reset()
