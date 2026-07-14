# 📡 Reliable Sources Reference — 给 Hermes 用的新闻 / 数据源

> 用法：
> 1. 拷到 `/vault/Config/Reliable-Sources-Reference.md`
> 2. 告诉 Hermes："use this list when running news routines"
> 3. 每月看一次，更新失效 link 或加新源
>
> Last Updated: 2026-07-15 · Author: Geewoni × Henry

---

# 🇺🇸 美股 / 美国财经 Top 10

## 1. **WSJ (Wall Street Journal)** Markets ⭐⭐⭐ 主源
- URL: https://wsj.com/news/markets
- RSS: `https://feeds.a.dj.com/rss/RSSMarketsMain.xml`
- Why: 题目质量最高 · headline free · 可靠不挂
- Use case: morning_news 主源

## 2. **WSJ US Business**
- URL: https://wsj.com
- RSS: `https://feeds.a.dj.com/rss/WSJcomUSBusiness.xml`
- Why: 企业新闻 · earnings / M&A / corporate
- Use case: 个股企业面

## 3. **MarketWatch**
- URL: https://marketwatch.com
- RSS: `https://feeds.content.dowjones.io/public/rss/RSSMarketsMain`
- Why: 不要钱的 WSJ 子站 · 分析评论好
- Use case: 评论 / 大盘趋势

## 4. **Seeking Alpha**
- URL: https://seekingalpha.com
- RSS: `https://seekingalpha.com/feed.xml`
- Why: 分析师 / 散户深度文章 · earnings call summary
- Use case: 个股深入研究

## 5. **Yahoo Finance** (注意: RSS 经常 429 限速)
- URL: https://finance.yahoo.com
- RSS: `https://finance.yahoo.com/news/rssindex`
- Why: 免费 + 全 · yfinance Python 库免费拿数据
- Use case: 备用源 · yfinance 数据

## 6. **Google News — US Stocks** ⭐ 稳定聚合
- RSS: `https://news.google.com/rss/search?q=US+stock+market+OR+S%26P+500+OR+Nasdaq&hl=en-US&gl=US&ceid=US:en`
- Why: 聚合多家源 · Google 托管不会挂
- Use case: 兜底 + 发现小源

## 7. **SEC EDGAR** ⭐ 数据宝藏
- URL: https://www.sec.gov/edgar
- API: https://www.sec.gov/edgar/sec-api-documentation
- Why: 官方 · 所有 10-K / 10-Q / 8-K 财报 · 内部交易披露
- Use case: Hermes 自动监控你 portfolio 公司财报

## 8. **Federal Reserve (FRED)** ⭐ 宏观数据
- URL: https://fred.stlouisfed.org
- API: free, register key
- Why: 美联储官方经济数据 · GDP / CPI / 失业率 / 利率 · 81 万个 series
- Use case: 宏观分析背景

## 9. **The Information** ⭐ 科技股内幕
- URL: https://theinformation.com
- Why: 硅谷科技股最深度 · paywalled 但值得（$400/年）
- Free alternative: 看他们的免费 Briefings
- Use case: 科技股内部消息（NVDA, AAPL, MSFT, GOOGL...）

## 10. **AP Business**
- URL: https://apnews.com/hub/business
- RSS: `https://feedx.net/rss/ap.xml` (third-party)
- Why: 通讯社 · 政治 / 政策影响市场时第一时间
- Use case: 政策事件影响

---

# 🇲🇾 马来西亚财经 Top 10

## 1. **Free Malaysia Today (FMT)** ⭐⭐⭐ 主源
- URL: https://www.freemalaysiatoday.com/category/business/
- RSS: `https://www.freemalaysiatoday.com/category/business/feed/`
- Why: **马股唯一稳定 RSS** · 英文 · 更新快 · 覆盖广
- Use case: morning_news MY 主源

## 2. **Google News — Malaysia Stocks** ⭐ 稳定聚合
- RSS: `https://news.google.com/rss/search?q=Bursa+Malaysia+OR+KLCI+OR+malaysia+stock&hl=en-MY&gl=MY&ceid=MY:en`
- Why: 聚合 Edge/Star/NST/Malay Mail 等多家 · Google 托管不会挂
- Use case: 兜底 + 聚合多家

## 3. **The Edge Malaysia** (网站重命名, RSS 已失效)
- URL: https://theedgemalaysia.com (原 theedgemarkets.com)
- RSS: ❌ 已失效 → 通过 Google News Malaysia 聚合获取
- Why: 马股最深度 · 通过 Google News 间接获取
- Use case: 聚合源内容

## 4. **The Star Business** (RSS 已失效)
- URL: https://www.thestar.com.my/business
- RSS: ❌ 已失效 → 通过 Google News Malaysia 聚合获取
- Why: 马来西亚最大英文报 · 通过 Google News 间接获取
- Use case: 聚合源内容

## 5. **Bursa Malaysia** 官方
- URL: https://www.bursamalaysia.com
- RSS: ❌ 被 Cloudflare 拦截
- Why: 所有公司公告先在这 · 需要 browser 抓取
- Use case: 监控 portfolio 公司公告

## 6. **NST Business** (New Straits Times)
- URL: https://www.nst.com.my/business
- RSS: ❌ 被 Cloudflare 拦截
- Why: 英文报老牌 · 需要 browser 抓取
- Use case: 通过 Google News 间接获取

## 7. **Bank Negara Malaysia (BNM)** ⭐ 央行
- URL: https://www.bnm.gov.my
- RSS: ❌ CloudFront 错误
- Why: 央行官方 · OPR 利率决策 / 货币政策 / 经济指标
- Use case: 利率变化必看（手动访问）

## 8. **KLSE Screener** ⭐ 散户神器
- URL: https://www.klsescreener.com
- Why: 免费 · 马股筛选 / 财报数据 / community 讨论
- Use case: Hermes 自动股票筛选

## 9. **i3investor**
- URL: https://klse.i3investor.com
- Why: 马股散户论坛 · 大量讨论 / blog 文章
- Use case: 散户情绪指标（contrarian indicator）

## 10. **BFM89.9** 电台 podcast
- URL: https://www.bfm.my
- Podcasts: 商业台 · 采访 / 评论
- Why: 唯一专业商业电台 · 嘉宾深度
- Use case: 通勤听 / 之后 Hermes 用 Whisper 转写

### Bonus · 中文媒体
- **Sin Chew Daily 财经** (sinchew.com.my)
- **Nanyang Siang Pau** (enanyang.my)
- **南洋商报财经** - 中文世界的马股

---

# 🤖 AI 相关 Top 10（综合：newsletter + Twitter + GitHub + 公司）

## 1. **Latent Space (Swyx)** ⭐ 必订
- Newsletter: https://latent.space
- Discord: 顶级工程师讨论
- Why: 每周深度 · 行业地图最清晰 · 工程师视角
- Free · Henry's #1 pick

## 2. **The Batch (Andrew Ng / DeepLearning.AI)**
- URL: https://www.deeplearning.ai/the-batch/
- Why: Andrew Ng 出 · 不夸张不焦虑 · 教育视角
- Free · 周报最适合入门

## 3. **Import AI (Jack Clark)** ⭐ Policy + Tech
- URL: https://jack-clark.net (or import.ai)
- Why: Anthropic co-founder Jack Clark 出 · policy + research
- Free · 深度且 honest

## 4. **Hacker News** ⭐ AI Front Page
- URL: https://news.ycombinator.com
- Why: 真实工程师讨论 · 排算法自动过滤垃圾
- 直接看就好

## 5. **r/LocalLLaMA** ⭐ 本地 AI 玩家
- URL: https://reddit.com/r/LocalLLaMA
- Why: 本地 LLM 圈最准实测 · 跟 Henry 项目最对口
- 每天逛 10 分钟

## 6. **Andrej Karpathy** Twitter ⭐ 顶级解读
- Twitter: @karpathy
- Why: OpenAI 元老 · 现独立 · 解读最准
- Bonus: 他的 YouTube 视频更深

## 7. **Simon Willison** ⭐ 实操王
- URL: https://simonwillison.net
- Twitter: @simonw
- Why: 每天测最新模型 · 长博客文章实测
- 还出了 `llm` CLI 工具

## 8. **Anthropic** 官方
- Blog: https://anthropic.com/news
- Twitter: @AnthropicAI
- Why: Claude 出品 · research paper · agent best practices
- 必看 "Building effective agents" 那篇

## 9. **HuggingFace Daily Papers** ⭐ 学术
- URL: https://huggingface.co/papers
- Daily Newsletter 可订
- Why: 每天精选 AI 论文 · 社区 vote 排序
- 跟得上学术前沿

## 10. **awesome-llm-apps** GitHub ⭐ 灵感库
- URL: https://github.com/Shubhamsaboo/awesome-llm-apps
- Why: 25k stars · 各种 LLM 应用 examples · 每周更新
- 找想 fork 的项目源

### Bonus Layer

**额外值得知道**：
- **Goose** (Block) — agent 框架黑马
- **Mastra** — TS agent (Vercel 系)
- **DSPy / Outlines / Instructor** — Python LLM 库三神器
- **Manus** / **OpenManus** — 全自主 agent
- **The Information AI section** — 硅谷内幕
- **Stratechery (Ben Thompson)** — 战略分析

---

# 🗂 给 Hermes 的指令模板

放进 Hermes system prompt 或 morning_news skill：

```yaml
news_sources:
  morning_economic:  # 早晨 7:30
    primary:
      - https://www.theedgemarkets.com/rss.xml
      - https://feeds.reuters.com/reuters/businessNews
      - https://www.cnbc.com/id/15839069/device/rss/rss.html
    backup:
      - https://feeds.content.dowjones.io/public/rss/RSSMarketsMain
    
  ai_news_evening:  # 晚上 21:00
    primary:
      - hackernews_top: 10
      - https://www.deeplearning.ai/the-batch/feed/
      - reddit_r_localllama_top: 10
    twitter_users:
      - karpathy
      - simonw
      - swyx
    
  monitored_companies:
    # 监控 SEC filings + Bursa announcements
    us:
      - NVDA
      - AAPL
      - MSFT
    my:
      # 你的 KLSE portfolio
      - MAYBANK
      - CIMB
      - 等等

  data_apis:
    - yfinance: free, no key
    - alpha_vantage: free tier (5 calls/min)
    - fred: free, register key needed
    - sec_edgar: free official
    - bursa: scrape if needed (no official API)
```

---

# 🔄 维护节奏

**月度**：
- 检查 RSS link 是否还活着
- 加新发现的源
- 删不再有价值的

**季度**：
- 评估每个源的"信号噪音比"
- 砍掉低信号源
- 升级到更深度源

---

**Document Version**: v1.0
**Henry's #1 picks** (5 个最不能少的)：
- 美股：Yahoo Finance + Reuters
- 马股：The Edge Markets
- AI：Latent Space + r/LocalLLaMA