from datetime import datetime, timezone
from lightweight_charts import Chart
import pandas as pd

OB_COLOR_MAP = {"BUY": "#3179f5", "SELL": "#f77c80"}


def normalize(df: pd.DataFrame):
    df.rename(columns={"ts_event": "time"}, inplace=True)
    df["time"] = pd.to_datetime(df["time"])
    return df


if __name__ == "__main__":
    chart = Chart()

    # Columns: time | open | high | low | close | volume
    df_bars = pd.read_csv("playground/bars.csv").drop(["ts_init", "bar_type", "type"], axis=1)

    # ts_event,type,bar_type,open,high,low,close,volume,ts_init
    df_bars = normalize(df_bars)
    chart.set(df_bars)

    # Columns: | low | high | ts_event | OrderBlockType
    df_ob = pd.read_csv("playground/ob.csv")
    df_ob = normalize(df_ob)

    for index, ob in df_ob.iterrows():
        chart.box(
            start_time=ob["time"],
            end_time=df_bars["time"].iloc[-1],
            start_value=ob["low"],
            end_value=ob["high"],
            color=OB_COLOR_MAP[ob["OrderBlockType"]],
        )

    chart.show(block=True)
