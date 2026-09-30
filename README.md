# kairos-research · Kairos 系列真实数据研究结论报告集

> 本仓库是 Kairos 量化系列的 **capstone 文档/分析仓库**：把 `kairos-factor`、`kairos-ml`、`kairos-portfolio`、`kairos-risk`、`kairos-backtest`、`kairos-execution`、`kairos-crypto`、`kairos-strategies`、`kairos-lab` 各仓库**已提交的真实数据实验产物**综合成连贯、准确、诚实的研究结论报告集。
>
> **铁律**：本仓库不实现算法、不重跑实验；每个数字都**实际读取自源仓库的产物文件**并标注来源（仓库/文件）。负结果（无稳健单因子 alpha、ML 样本外无预测力、多数择时跑不赢等权基准）如实呈现，不美化。**全部内容仅供研究，不构成投资建议。**

## 研究计划总览

Kairos 系列在同一批真实行情（38 只 A 股 + 14 只跨资产 ETF，来自 `kairos-data`，只读）上各自跑了独立实验。本仓库的工作是**阅读这些已提交的 `REPORT.md` / `metrics.json` / `*.csv`，抽取真实数字，按主题重组成 11 篇结论笔记**，并保证每个关键数字可溯源、每篇结论有「背景 → 数据与方法 → 结果 → 解读 → 局限」的统一结构。

研究方法上的三条自律：

| 原则 | 做法 |
|---|---|
| 数字真实可溯源 | 每个关键数字后标注 `(来源: kairos-xxx/research/...)`；机读汇总见 `data/key_findings.csv` |
| 诚实优先 | 负结果照写；源报告内部的口径矛盾（如回测回撤叙述）以 `metrics.json` 的真实数值为准并指出 |
| 离线可复现 | `tests/test_notes.py` 离线校验笔记齐全、来源标注、CSV 可读、README 索引文件存在；兄弟仓库缺失时溯源用例自动 skip |

仓库布局：`README.md`（本文）、`notes/`（11 篇笔记）、`data/key_findings.csv`（关键指标机读汇总）、`tests/test_notes.py`（离线测试）、`Makefile` / `pyproject.toml` / `LICENSE` / `.gitignore` / `.github/workflows/ci.yml`。

## 关键结论（10 条，每条一句话 + 真实数字 + 来源）

- 该 A 股池找不到可实盘的单因子 alpha：16 个（样本×因子×预处理）组合中，非重叠口径 |t|≥2 的有 **0 个**，最大 |秩 IC| 仅 **0.0161**（momentum_20）。(来源: kairos-factor/research/real_factor/REPORT.md)
- ML 在样本外无正向预测力：6 个（模型×CV）组合中日频 IC t≥+2 的有 **0 个**，达到显著的 2 个全为负（最差 walk-forward/GBM IC=**-0.0163**、t=**-2.66**）。(来源: kairos-ml/research/real_ml/REPORT.md)
- 裸因子 rv10（样本外日频 IC=**-0.0396**、t=**-5.00**）强于任何 16 特征 ML 组合（模型最大 |IC|=0.0163）：低波动异象是唯一稳健信号，却被模型稀释。(来源: kairos-ml/research/real_ml/metrics.json)
- 真实 A 股组合（38 只 inverse_vol）的分散化被相关性吃掉：分散化比率 DR 仅 **1.77**（零相关上界 √n=6.16），**94.58%** 方差来自单一市场因子（组合 beta 0.85）。(来源: kairos-risk/research/real_risk/risk_metrics.json)
- 该组合尾部显著肥于正态：Hill ξ=**0.449**、GPD ξ=0.214，99.9% POT VaR **4.98%**（≈497.5 万元）是正态法（2.85%）的 1.7 倍；MDD **23.95%**、水下时间 **94.12%**。(来源: kairos-risk/research/real_risk/risk_metrics.json)
- 回测过拟合的代价：同一历史夏普 PSR=**0.983**，但承认是在 38 只里挑组合（N=38）后 DSR 降到 **0.480**、N=100 时仅 **0.341**。(来源: kairos-risk/research/real_risk/risk_metrics.json)
- 多资产风险平价/全天候最稳健：扩到 14 只 ETF（6 个资产类别、2210 期）后，all_weather 夏普 **1.5169**、MDD **5.12%**，e2e 滚动 risk_parity 夏普 **1.3002**、MDD **6.55%**，而等权基准夏普仅 **0.5924**、MDD **17.06%**。(来源: kairos-strategies/research/real_multi/SUMMARY.md；kairos-lab/research/e2e_multi_asset/REPORT.md)
- 106 策略锦标赛：去相关精英组合夏普 **0.93**、MDD **15.20%**，跑赢等权基准（夏普 0.76、MDD 31.21%）且回撤减半，但绝对收益（64.9%）不及基准（145.3%）——组合的价值在降回撤而非增收益。(来源: kairos-strategies/research/tournament/selection.json)
- 真实 A 股向量化动量 Top5 **全面跑输**等权买入持有：累计 **106.37% vs 143.30%**、夏普 0.49 vs 0.66，且最大回撤更深（**55.22% vs 44.92%**）。(来源: kairos-backtest/research/real_backtest/metrics.json)
- 加密实时源在采集环境不可达，改用真实黄金 ETF 历史 bar 回放：momentum/grid/dca 三策略纸面收益（+125%/+17%/+150%）**全部跑不赢**买入持有（**+234.58%**），会计四恒等式全过。(来源: kairos-crypto/research/real_replay/metrics.json)

## 笔记索引

| 笔记 | 主题 | 一句话结论 |
|---|---|---|
| [notes/00-overview.md](notes/00-overview.md) | 数据与方法总览 | 38 只 A 股 + 14 只 ETF（6 个资产类别、2210 个交易日）、hfq 口径、防未来、各仓库成本设定与可复现 |
| [notes/01-anomaly-map.md](notes/01-anomaly-map.md) | 异象/因子图谱 | 极短期反转、一个月动量、三个月再反转；低波是唯一稳健异象；近半信号是行业 beta |
| [notes/02-ml-vs-factor.md](notes/02-ml-vs-factor.md) | ML vs 单因子 | ML 样本外无正向预测力，反而稀释了有效的低波单因子 |
| [notes/03-multi-asset.md](notes/03-multi-asset.md) | 多资产配置 | 全天候/风险平价/GTAA/60-40 对比；风险平价不依赖期望收益故稳健，但绝对收益偏低 |
| [notes/04-tournament.md](notes/04-tournament.md) | 106 策略锦标赛 | 85/106 策略同属一相关簇；精英组合降回撤但收益不及基准 |
| [notes/05-risk-tail.md](notes/05-risk-tail.md) | 组合风险与尾部 | VaR/ES 多口径、成分可加、系统性 94.58%、肥尾 Hill/GPD、PSR/DSR 打折 |
| [notes/06-strategy-robustness.md](notes/06-strategy-robustness.md) | 样本外验证 | 四维（PSR/CI/正窗/敏感性）联看；稳健的都是低参数趋势/季节/配置类 |
| [notes/07-execution-tca.md](notes/07-execution-tca.md) | 执行 TCA | TWAP/VWAP/IS 对比；算法优劣由窗口漂移方向决定，非绝对 |
| [notes/08-crypto-replay.md](notes/08-crypto-replay.md) | 加密纸面回放 | 实时源不可达→真实 bar 回放；三策略均跑不赢买入持有，会计自洽 |
| [notes/09-data-methodology.md](notes/09-data-methodology.md) | 数据完整性方法论 | qfq 出负价/假收益→切 hfq；停牌/上市/非正价处理与留痕；可复现 |
| [notes/10-limitations.md](notes/10-limitations.md) | 局限 | 幸存者/选择偏差、单一 universe、过拟合、成本缺失、非投资建议 |

## 机读数据

[data/key_findings.csv](data/key_findings.csv) 汇总了从各报告抽取的关键指标，列为 `指标,值,单位,来源仓库,来源文件,备注`，便于程序化核对与溯源。每条的 `(来源仓库, 来源文件)` 都指向真实存在的兄弟仓库产物文件（离线测试会校验，兄弟仓库缺失时自动 skip）。

## 测试与复现

```bash
cd kairos-research
python3 -m pytest -q          # 离线测试全绿
python3 -c "import csv;print(sum(1 for _ in csv.reader(open('data/key_findings.csv'))),'rows in key_findings')"
make check                    # = pytest + 打印 key_findings 行数
```

CI（`.github/workflows/ci.yml`）在 push/PR 时用 Python 3.9/3.11 跑 `pip install pytest pandas && pytest -q`。本仓库无重依赖、不含可导入的 Python 包。

## 许可

MIT，版权行 `Copyright (c) 2026 Bruce848647703`，见 [LICENSE](LICENSE)。本仓库为原创撰写的研究综合，未复制任何第三方代码；所有引用数字版权归原作者/数据源所有。

## 免责声明

本仓库全部内容为对 Kairos 系列真实数据历史实验结果的研究性综合，所有数字均引自各源仓库已提交的产物文件并标注来源。结论仅描述特定样本内的历史统计特征，**不代表未来收益，不构成任何投资建议**。详见 [notes/10-limitations.md](notes/10-limitations.md)。
