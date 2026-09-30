# 08 · 加密纸面交易在真实历史 bar 上的回放

> 问题：加密货币纸面交易引擎能否在真实历史 bar 上正确运行、会计自洽？momentum / grid / dca 三种策略表现如何？
> 数据：`kairos-crypto/real_replay`——**加密实时源在采集环境不可达**，故用真实黄金 ETF 历史 OHLCV（后复权）回放驱动并验证引擎。

## 背景 / 问题

`kairos-crypto` 的目标是加密货币纸面交易（无任何真实下单）。但本系列铁律禁止联网抓取，且**加密实时源（binance 等）在当前运行环境被网络阻断**，无法采集真实加密行情。为了仍能**在真实数据上验证引擎与策略**，改用真实历史 bar 回放 (来源: kairos-crypto/research/real_replay/REPORT.md 第 0 节)。

## 数据与方法

- **加密实时源不可达的诚实说明**：binance 等真实加密交易所接口在本运行环境被网络阻断，且铁律禁止任何真实联网抓取；因此改用**真实历史 OHLCV bar 回放**来驱动并验证纸面交易引擎 (来源: kairos-crypto/research/real_replay/REPORT.md；metrics.json `meta.disclaimer`)。
- 价格序列：真实黄金 ETF `sh518880`（后复权 hfq），映射为交易对 `SH518880/CNY`（文件名作 BASE、CNY 作计价币标签），**仅作为「通用价格序列」使用**——引擎与策略代码与标的无关；接入真实加密数据的方式是自行下载历史 K 线 CSV 交给 `load_candles()`，或继承 `Exchange` 实现实时适配器 (来源: kairos-crypto/research/real_replay/REPORT.md)。
- 区间 2013-07-29 ~ 2026-09-24、**3202 根日线 bar**；首末收盘 0.9920 → 3.3190（买入持有 **+234.58%**） (来源: kairos-crypto/research/real_replay/metrics.json `meta`)。
- 初始资金 10,000 CNY、手续费率 0.0500%、`slippage_bps=0`；年化期数按真实时间跨度估计 ≈243.2（A 股交易日口径；若为加密 24/7 小时线会自动得到 ≈8760） (来源: kairos-crypto/research/real_replay/REPORT.md)。
- 防未来：市价单按当根收盘价成交，限价单挂出后只能由**后续** K 线触及撮合 (来源: kairos-crypto/research/real_replay/REPORT.md)。

## 结果

### 1. 三策略纸面交易结果（真实 bar 回放）

| 策略 | 期末净值 | 总收益 | 年化 | 夏普 | 最大回撤 | 成交笔数 | 手续费 | 会计自洽 |
|---|---|---|---|---|---|---|---|---|
| momentum | 22,531.96 | +125.32% | +6.36% | 0.57 | 32.48% | 103 | 672.04 | 通过 |
| grid | 11,660.98 | +16.61% | +1.17% | 0.31 | **12.07%** | 139 | 70.99 | 通过 |
| dca | 24,997.59 | **+149.98%** | +7.21% | **0.70** | 29.77% | 153 | **4.75** | 通过 |
| **买入持有基准** | — | **+234.58%** | — | — | — | — | — | — |

(来源: kairos-crypto/research/real_replay/metrics.json `strategies`；REPORT.md 第 3 节)

- **三种策略全部跑不赢买入持有（+234.58%）**：在这段黄金 ETF 长期单边上行行情里，dca（+149.98%）最接近、momentum（+125.32%）次之、grid（+16.61%）最差。
- 补充观察：momentum 期末仍持多（end_state=long，final_base 6788.78）；dca 定投 153 次、累计投入 9499.77、平均成本 1.2871；grid 完成 71 个网格周期（买 67/卖 71）、期末 final_base≈0（**底仓被卖光**）、尚有 8 张挂单 (来源: kairos-crypto/research/real_replay/metrics.json `extras`)。

### 2. grid 为什么最差（诚实呈现，不美化）

网格策略的中心价锚定在**首根 bar**，在长期单边上行趋势中底仓会被早期逐步卖光、网格随之失效——这是策略特性使然，报告如实呈现：grid 期末 final_base_balance≈0、总收益仅 +16.61%（远低于买入持有 +234.58%），但**最大回撤也最低（12.07%）**，体现了网格「牺牲趋势收益换低回撤」的本质 (来源: kairos-crypto/research/real_replay/REPORT.md 第 6 节；metrics.json)。

### 3. 会计自洽校验（引擎正确性）

每个策略独立验证四条恒等式，**全部通过**：① 净盈亏 = 毛盈亏 − 手续费合计；② 手续费合计 = Σ 逐笔成交 fee；③ 期末净值 = 计价币余额（含冻结）+ 持仓市值；④ 净值曲线无 NaN 且恒为正 (来源: kairos-crypto/research/real_replay/REPORT.md 第 4 节；metrics.json `checks`)。这证明 PaperTradingEngine 在真实 bar 上的撮合与记账是正确的。

## 解读

- 本篇的价值**不在「加密策略有多赚」**，而在两点：(1) 诚实说明**加密实时源在采集环境不可达**，用真实历史 bar 回放这一合规替代验证了引擎；(2) 在真实数据上暴露了策略的固有特性——单边上行行情里**简单买入持有最难打败**，grid 因底仓卖光而失效，dca 因持续摊薄成本而最接近基准。
- 这与其它仓库的结论一致：在幸存者偏差/单边趋势样本里，被动持有是极强的基线（参见 [06](06-strategy-robustness.md) 等权基准四维过关、[04](04-tournament.md) 精英组合收益不及基准）。

## 局限 / 后续

- 用黄金 ETF 作「通用价格序列」，**并非真实加密行情**；加密的 24/7、高波动、折溢价、最小申报单位等特性未被覆盖。
- 日线收盘价近似成交，未建模盘中流动性、ETF 折溢价、分红税；纸面撮合假设限价单被触及即全额成交，无排队与部分成交 (来源: kairos-crypto/research/real_replay/REPORT.md 第 6 节)。
- 后续：在可联网环境自行下载真实加密历史 K 线 CSV 交给 `load_candles()` 重跑，或实现 `Exchange` 实时适配器；把年化口径切到 8760（小时线）复核夏普。

> 相关笔记：执行/撮合的防未来与成本口径见 [07-execution-tca.md](07-execution-tca.md)；「被动持有难打败」的旁证见 [04-tournament.md](04-tournament.md)、[06-strategy-robustness.md](06-strategy-robustness.md)。
