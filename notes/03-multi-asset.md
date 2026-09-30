# 03 · 真实多资产：全天候 / 风险平价 / GTAA / 60-40

> 问题：在真实 9 只跨资产 ETF 上，全天候、风险平价、GTAA、60/40 的收益-风险-回撤各是什么？为什么风险平价/全天候类在风险调整后最稳健，却绝对收益偏低？
> 数据：`kairos-strategies/real_multi`（9 ETF、2354 期、单边成本 0.05%）+ `kairos-lab/e2e_multi_asset`（滚动再平衡、成本 0.1%）+ `kairos-portfolio/real_portfolio`（静态优化）。

## 背景 / 问题

A 股单池找不到稳健 alpha（[01](01-anomaly-map.md)/[02](02-ml-vs-factor.md)），自然的出路是**跨资产分散**。本篇用真实 ETF（A 股/海外股/黄金/国债/货币）比较四类经典多资产框架，并解释风险平价为何稳健。

## 数据与方法

- 9 只 ETF、5 个资产类别；样本 2017-01-18 ~ 2026-09-24/28，2353~2354 个交易日 (来源: kairos-portfolio/research/real_portfolio/REPORT.md；kairos-lab/research/e2e_multi_asset/REPORT.md)。
- 横截面平均相关系数 **0.2097**（最小/最大 -0.217 / 0.854）——黄金/国债与 A 股权益低甚至负相关，是分散的来源 (来源: kairos-lab/research/e2e_multi_asset/REPORT.md)。
- 各资产样本内表现：纳指 ETF sh513100 累计 5.31（年化 21.81%，夏普 0.9452）、黄金 sh518880 累计 2.27（年化 13.54%，夏普 0.8678）、国债 sh511010 累计 0.31（年化 2.91%，夏普 **1.4729**、MDD 仅 4.87%） (来源: kairos-lab/research/e2e_multi_asset/REPORT.md)。

## 结果

### 1. 四类多资产框架对比（`kairos-strategies/real_multi`，单边成本 0.05%）

| 策略 | 累计收益 | CAGR | 波动 | 夏普 | 索提诺 | 最大回撤 | 卡玛 |
|---|---|---|---|---|---|---|---|
| **all_weather（全天候）** | 65.50% | 5.54% | 3.27% | **1.6665** | 2.4330 | **4.92%** | **1.1267** |
| risk_parity_alloc（风险平价） | 11.01% | 1.12% | 1.08% | 1.0400 | 1.6221 | 1.81% | 0.6205 |
| inverse_vol（逆波动） | 12.50% | 1.27% | 1.32% | 0.9583 | 1.4178 | 1.82% | 0.6988 |
| max_diversification | 10.28% | 1.05% | 1.05% | 1.0059 | 1.5938 | 1.89% | 0.5580 |
| **gtaa（全球战术配置）** | **113.06%** | 8.43% | 12.26% | 0.7223 | 0.9926 | 13.73% | 0.6141 |
| **sixty_forty（60/40）** | 73.25% | 6.06% | 10.97% | 0.5910 | 0.8404 | 20.44% | 0.2965 |
| equal_weight_rebal（等权再平衡） | 92.21% | 7.25% | 12.54% | 0.6209 | 0.8801 | 23.79% | 0.3046 |
| equal_weight_buy_hold（基准） | 92.42% | 7.26% | 12.56% | 0.6208 | 0.8808 | 23.95% | 0.3031 |

(来源: kairos-strategies/research/real_multi/SUMMARY.md)

> 排序很清晰：**按夏普/回撤，全天候 > 风险平价 ≈ 逆波动 > GTAA > 60/40 ≈ 等权**；按绝对收益则反过来，GTAA（113%）> 等权（92%）> 60/40（73%）> 全天候（65%）>> 风险平价（11%）。风险调整与绝对收益在此**显著背离**。

### 2. 滚动再平衡口径（`kairos-lab/e2e_multi_asset`，成本 0.1%）

| 组合 | 累计收益 | 年化 | 年化波动 | 夏普 | 最大回撤 | 卡玛 | 年化换手 |
|---|---|---|---|---|---|---|---|
| **risk_parity** | 0.5995 | 5.16% | 4.60% | **1.1166** | **7.65%** | 0.6739 | 1.78 |
| equal_weight | 0.9077 | 7.16% | 12.56% | 0.6135 | 24.06% | 0.2975 | 1.84 |
| inverse_vol | 0.0781 | 0.81% | 1.01% | 0.8041 | 1.56% | 0.5195 | 0.74 |

(来源: kairos-lab/research/e2e_multi_asset/REPORT.md)

- risk_parity 风险体检：历史 VaR95（每日）0.40%、ES95 0.69%、偏度 -0.7277、超额峰度 9.9390、**PSR 0.9995、DSR（5 trials）0.9842** (来源: kairos-lab/research/e2e_multi_asset/REPORT.md)。
- 期末风险平价把 **91.12%** 权重给了国债 sh511010；按资产类别归集的风险贡献：cn_equity 46.38%、global_equity 34.50%、commodity 11.30%、bond 7.82%、cash 0 (来源: kairos-lab/research/e2e_multi_asset/REPORT.md)。

### 3. 静态优化口径（`kairos-portfolio/real_portfolio`，样本内）

| 方案 | 年化收益 | 年化波动 | 夏普 | 日 VaR95 | 分散化比率 DR | 最大成分风险占比 |
|---|---|---|---|---|---|---|
| 等权 | 7.91% | 12.55% | 0.630 | 1.15% | 1.392 | 21.6% |
| 最大夏普 | 4.45% | 2.25% | **1.976** | 0.21% | 1.768 | 57.6% |
| 均值方差（λ=15） | **10.75%** | 7.36% | 1.461 | 0.67% | 1.498 | 58.4% |
| **风险平价** | 0.68% | 0.53% | 1.285 | 0.05% | **2.143** | **11.1%** |
| 最小方差 | 0.03% | 0.23% | 0.151 | 0.02% | 1.249 | 99.1% |

(来源: kairos-portfolio/research/real_portfolio/REPORT.md)

- 风险平价把 **85.92%** 权重给货币 ETF sh511990、10.53% 给国债，但每个资产的**成分风险占比严格 = 1/9 = 11.11%**，最大偏离仅 **6.57e-13**（定点迭代自研解，精确成立） (来源: kairos-portfolio/research/real_portfolio/REPORT.md；weights.csv)。

## 解读：为什么风险平价稳健

1. **不依赖期望收益估计**：风险平价只用协方差、按成分风险贡献相等分配，避开了均值-方差对期望收益高度敏感、易出极端角点解、且样本内最大夏普（1.976）存在前视/过拟合的问题 (来源: kairos-portfolio/research/real_portfolio/REPORT.md)。
2. **天然防御 / 全天候**：高波动资产（成长/海外权益）权重被压低、低波动资产（国债）被抬高，波动与回撤随之被压到很低——三种口径下 risk_parity/全天候的夏普都 ≥1.0、MDD 都远低于等权（如 e2e：7.65% vs 24.06%） (来源: kairos-lab/research/e2e_multi_asset/REPORT.md；kairos-strategies/research/real_multi/SUMMARY.md)。
3. **分散度最高**：静态风险平价 DR=2.143（全场最高）、最大成分风险占比仅 11.1%（≈1/n） (来源: kairos-portfolio/research/real_portfolio/REPORT.md)。
4. **显著性高**：e2e risk_parity 的 PSR 0.9995、DSR（5 trials）0.9842，是各组合里最经得起多重检验打折的 (来源: kairos-lab/research/e2e_multi_asset/REPORT.md)。

**但必须诚实指出代价**：

- **绝对收益偏低**：不加杠杆时「等风险贡献」会把约九成权重压给低波动的国债/货币腿，组合波动被压得很低、夏普很高，但绝对收益塌缩（静态风险平价年化仅 0.68%、e2e 5.16%、strategies 1.12%）。真实的全天候组合靠**债券加杠杆**把总波动抬到目标水平，本样本 `max_leverage=1` 未启用 (来源: kairos-lab/research/e2e_multi_asset/REPORT.md；kairos-portfolio/research/real_portfolio/REPORT.md)。
- **现金腿会捕获纯风险配置**：货币 ETF（年化波动仅 0.23%）若一并纳入等风险贡献，会吸走 >90% 权重、组合退化为持币，故 e2e 流水线把 cash 腿排除在风险平价求解之外 (来源: kairos-lab/research/e2e_multi_asset/REPORT.md)。
- **口径差异**：风险平价的累计收益在三个仓库分别为 11.01%（strategies，含 cash 腿、成本 0.05%）、59.95%（lab，排除 cash、成本 0.1%）、年化 0.68%（portfolio，静态样本内）——**不可跨仓库直接比较**，差异来自 cash 腿处理、成本、静态 vs 滚动。
- **δ=1 退化**：当黄金/国债与权益显著负相关、边际风险贡献为负时，风险平价无 long-only 内部解，求解器自动改用「相关系数全收缩到常相关目标」的协方差重解（仍属 Ledoit-Wolf 家族，未静默降级为等权） (来源: kairos-lab/research/e2e_multi_asset/REPORT.md)。

## 局限 / 后续

- 仅 9 个资产、2354 个交易日，PSR/DSR 受样本长度限制 (来源: kairos-lab/research/e2e_multi_asset/REPORT.md)。
- 期望收益采用已实现均值（前视），最大夏普/均值方差为**样本内**结果，实盘期望应显著更低 (来源: kairos-portfolio/research/real_portfolio/REPORT.md)。
- 后续：用 `--target-vol` + `max_leverage>1` 做波动率目标化、或显式指定各类别风险预算，把风险平价从「持币化」拉回可投资的收益-风险前沿。

> 相关笔记：A 股单池的成分风险/系统性占比见 [05-risk-tail.md](05-risk-tail.md)；多资产里的策略锦标赛见 [04-tournament.md](04-tournament.md)。
