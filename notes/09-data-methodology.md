# 09 · 数据完整性方法论：qfq 的坑 → hfq 的修复

> 问题：真实 A 股行情有哪些必须处理的口径陷阱？为什么从 qfq（前复权）切换到 hfq（后复权）？停牌/上市/非正价如何处理？怎样保证可复现？
> 数据：`kairos-data`（DATA_NOTICE、universe、ashare.py、git 提交）+ `kairos-risk.realdata` 的清洗留痕（risk_metrics.json）+ 各仓库 REPORT 的口径说明。

## 背景 / 问题

本系列不生产数据，只读 `kairos-data` 已提交的真实日线。真实数据有五个必须处理的口径问题，任何一个处理不当都会让下游所有结论失真。其中最隐蔽、影响最大的是**复权口径**。

## 数据与方法：qfq 的坑

### 前复权（qfq）为什么会出负价 / 假收益

- 该数据源的等差（减法）前复权是 `P_adj = P_raw − D_t`（`D_t` 为 t 日之后的累计分红）。对**长期高分红**标的，早年价格会被减到**接近 0 甚至为负** (来源: kairos-risk/research/real_risk/REPORT.md 第 0 节)。
- 价格趋零时，真实的小幅涨跌会被放大成**数倍的伪收益**：`pct_change` 得到的是被放大 `k = P_raw / P_adj` 倍的假收益，高分红标的的年化波动甚至能被放大到 **8000% 量级**（物理上不可能） (来源: kairos-risk/research/real_risk/REPORT.md)。
- 因此 `kairos-factor` 用「|单日涨跌| > 30%（远超 A 股 ±10%/±20% 涨跌停上界）」作为伪影筛查，并给出 clean/full 两个互补样本检验结论是否依赖窗口选择 (来源: kairos-factor/research/real_factor/REPORT.md)。

### 切换 hfq（后复权）的修复

- **数据层修复**：`kairos-data` 的提交 `783b23c` 明确将复权口径 **qfq → hfq**——「前复权出负价/假收益，后复权干净」，解析器支持 `hfqday`，并重抓 38 股 + 9 ETF 校验（该提交当时的 ETF 池为 9 只，属历史事实） (来源: kairos-data git 提交 783b23c；kairos_data/ashare.py)。
- **ETF 池其后已扩充**：`ASSET_CLASS_ETFS` 现为 **14 只 / 6 个资产类别**（新增 sh510050 上证50、sh510880 红利、sh513500 标普500、sh512100 中证1000、sh511260 十年国债；新增类别 `cn_value`），公共区间随之变为 **2017-08-24 ~ 2026-09-30、2210 个交易日**（起点由最晚上市的 sh511260 决定），hfq 口径与清洗规则不变 (来源: kairos-data/kairos_data/universe.py `ASSET_CLASS_ETFS`/`ASSET_CLASSES`；kairos-strategies/research/real_multi/NOTES.md；kairos-lab/research/e2e_multi_asset/REPORT.md)。
- hfq（后复权）价格水平被放大，但**收益率正确**，适合特征/标签与回测研究；`DATA_NOTICE` 最终口径即为后复权 hfq (来源: kairos-data/data/ashare/DATA_NOTICE.md；kairos-ml/research/real_ml/metrics.json `"adjust": "hfq(后复权)"`)。
- 各仓库口径：`kairos-ml` / `kairos-execution` / `kairos-crypto` / `kairos-lab` 用 **hfq**；`kairos-factor` / `kairos-backtest` / `kairos-risk` 的 REPORT 仍按 **qfq** 口径描述并附带修复机制（见下）。**跨仓库比较收益率时口径一致（都正确），但价格水平不可直接对齐。**

## 结果：清洗流水线的五步留痕（`kairos-risk.realdata`）

`kairos-risk` 把清洗的每一步都写进 `risk_metrics.json`，可审计 (来源: kairos-risk/research/real_risk/risk_metrics.json `data`)：

| 步骤 | 处理 | 本池实测 |
|---|---|---|
| ① 非正价 | 价格 ≤0/NaN → 记为缺失；裁剪到「全体标的均严格正价」的公共窗口 | 无效价 **0** 条；裁剪丢弃早期价 **23404** 条 → 区间起点 2018-10-16（而非数据最早的 2016 年） |
| ② 停牌/缺口 | 前向填充 ffill（当日无成交沿用前收盘价，即当日收益 0），只用历史、无未来函数 | 窗口内缺失单元格 **9** 个 |
| ③ 等差前复权放大收益 | 用涨跌停硬约束**反解每标的每日偏移下界 D̂**，令 `P_repaired = P_adj + D̂`；因 D̂ ≤ D_真，修复只会把伪收益拉回真实口径、**不会把风险修小** | 越界：修复前 **0** / 修复后 **0**；offset_max 全为 **0.0**（本池无需实际修复） |
| ④ 压缩过度无法修复 | 闸门 `max_compression=3.0`，超限整只剔除并记录原因与 k̂ | 剔除 **0** 只；compression_max 全为 **1.0** |
| ⑤ 残余越界观测 | 按 `on_bad=clip`（取同号涨跌停边界值，不低估尾部、不牵连同日其它标的） | 越界 **0** 个；连带删除交易日 **9** 天 |

- 最终分析样本：**38 标的 × 1921 交易日**，单日最大绝对收益 **19.75%**（落在涨跌停物理约束内）；年化波动横截面中位/最小/最大 = 0.2957 / 0.1051 / 0.4743 (来源: kairos-risk/research/real_risk/risk_metrics.json `data.summary`)。

> **诚实说明**：在**这个** 38 只大盘蓝筹池里，qfq 的伪影并未真正出现（0 条负价、修复前后越界均 0、偏移下界全 0）。也就是说上面的修复机制在本池是**防御性、留痕但几乎无实际改动**的——它的价值在于：换到含长期高分红/低价标的的池子时，同一套机制能识别并保守修复，且「D̂ 是下界」保证**只会把风险修大、不会修小**（残余偏差声明：高分红标的早期 2019-2021 收益仍可能被小幅高估、波动/VaR 偏保守） (来源: kairos-risk/research/real_risk/REPORT.md)。

### 其它仓库的清洗口径（一致原则）

- `kairos-backtest`：非正价 → NaN → ffill 桥接停牌 → 按全体上市日裁剪到公共有效区间，保证面板无缺口、无前视 (来源: kairos-backtest/research/real_backtest/REPORT.md)。
- `kairos-ml`：hfq，非正价与缺失值置 NaN 后按列 ffill（停牌沿用最后有效价） (来源: kairos-ml/research/real_ml/REPORT.md)。
- `kairos-portfolio`：非正价 → NaN、ffill 桥接停牌、按全体上市日裁剪为平衡面板（`load_close_panel`） (来源: kairos-portfolio/research/real_portfolio/REPORT.md)。

## 解读

- **复权口径是真实数据研究的第一道生死线**：qfq 的减法复权在高分红标的上会制造负价与数倍伪收益，足以把「低波动异象」「VaR」等结论彻底带偏。切换 hfq 后收益率正确、价格水平放大但不影响无量纲特征。
- **留痕比结果更重要**：`kairos-risk` 把「丢弃多少条、填充几个、修复前后越界多少、剔除哪只、为什么」全部写进 JSON，使数据完整性可审计、可复现，而不是黑箱清洗。
- **保守修复原则**：用涨跌停物理约束反解偏移**下界**，保证修复「只会把风险修大、不会修小」，是面对不可辨识伪影时的稳健工程选择。

## 局限 / 后续

- 前复权口径以数据源为准，可能存在少量口径误差；hfq 价格水平放大，只宜用收益率/比值类特征 (来源: kairos-ml/research/real_ml/REPORT.md)。
- 停牌 ffill 会低估当期波动；裁剪到公共正价窗口会丢弃早期历史（本池丢 23404 条）。
- 可复现：数据可由 `examples/fetch_real.py` 按 `universe.LIQUID_A_SHARES` / `etf_symbols()` 随时重抓；各仓库含 `tests/test_realdata.py` 离线校验 (来源: kairos-data/data/ashare/DATA_NOTICE.md；各仓库 REPORT 复现节)。
- 后续：统一到单一复权口径并重跑 factor/backtest/risk，消除跨仓库 qfq/hfq 混用；引入退市/长期停牌标的以缓解幸存者偏差（见 [10-limitations.md](10-limitations.md)）。

> 相关笔记：数据规模与 universe 见 [00-overview.md](00-overview.md)；清洗后风险度量见 [05-risk-tail.md](05-risk-tail.md)；幸存者/选择偏差见 [10-limitations.md](10-limitations.md)。
