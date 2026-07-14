// i18n.js — EN / ZH dictionary and apply function
// Language is stored in localStorage under the key "lang".
// Call window.applyI18n() to (re-)render all [data-i18n] elements.

window.I18N = {
  en: {
    // ── Navigation ──────────────────────────────────────────────────────────
    'nav.work':       'Work',
    'nav.how':        'How I Think',
    'nav.experience': 'Experience',
    'nav.skills':     'Skills',
    'nav.contact':    'Contact',
    'nav.resume':     'Resume ↓',
    'nav.demos':      'Demos',

    // ── Hero ────────────────────────────────────────────────────────────────
    'hero.tagline':     'Backend Team Lead',
    'hero.positioning': 'I design and ship the systems behind a 300k+ DAU real-money transaction platform — from legacy monolith to modern microservices, from requirement to production.',
    'hero.ctaContact':  'Get in touch',
    'hero.ctaResume':   'Download Resume',

    // ── Signature Work ──────────────────────────────────────────────────────
    'sig.heading': 'Signature Work',

    // ── How I Think ─────────────────────────────────────────────────────────
    'how.heading': 'How I Think',
    'how.p1.title': 'Price the risk before pricing the work.',
    'how.p1.proof': 'The first question is never "how long will it take" — it\'s "what breaks if this is wrong, and who feels it?" Failure cost decides engineering rigor: money-path modules get idempotency by design, staged rollouts and pre-launch index reviews; a cosmetic feature gets speed instead.',
    'how.p2.title': 'Design for the next change, not this delivery.',
    'how.p2.proof': 'Requirements on this platform change weekly. In every design review I ask which parts business will want to tune later — those become configuration, not code. A feature request should become an ops change, not a deploy.',
    'how.p3.title': 'Decompose by ownership, not by ticket.',
    'how.p3.proof': 'Big goals get split along module boundaries with explicit contracts — proto first, then parallel build. Each engineer owns one domain end-to-end; one floating engineer absorbs surges. People grow by owning, not by taking tasks.',
    'how.p4.title': 'Decide with evidence, commit with a rollback.',
    'how.p4.proof': 'Big technical choices get benchmarks and POCs, not opinions — and every migration ships with an escape hatch. If we can\'t measure it or can\'t undo it, we\'re not ready to decide.',
    'how.p5.title': 'Turn work into leverage.',
    'how.p5.proof': 'A bug fixed is a cost; a bug turned into a playbook or a bot is an asset. Anything done twice becomes a tool: integration SDKs, incident playbooks, an AI diagnosis bot the whole team runs.',

    // ── Demos ───────────────────────────────────────────────────────────────
    'demos.heading': 'Demos & Tooling',

    // ── Experience ──────────────────────────────────────────────────────────
    'experience.heading': 'Experience',

    'experience.role1.meta':    '2026 – present · Alor Setar, Malaysia',
    'experience.role1.title':   'Team Lead, Backend Platform',
    'experience.role1.company': 'SN Soft Sdn Bhd',
    'experience.role1.summary': '1 senior + 3 mid engineers across four module domains, dual-stack (legacy monolith + microservices) plus third-party provider integration. Architecture gatekeeper for cross-team requirements; grow engineers through ownership and calibrated challenges — three juniors grown to the point of running an entire production platform themselves, requirements negotiation included. One engineer floats to wherever the pressure is — the same seat I grew up in.',

    'experience.role2.meta':    'Dec 2019 – 2026 · 7 years · Malaysia',
    'experience.role2.title':   'Backend Engineer → Acting Tech Lead',
    'experience.role2.company': 'SN Soft Sdn Bhd',
    'experience.role2.summary': 'Seven years, 2,000+ merged PRs, from full-stack on the legacy platform to pioneering the new stack. Highlights beyond the case studies: hardened withdrawal flows (dual-pending prevention, cancellable states, auto-review conditions), C2C order matching grafted onto the workflow state machine (50+ PRs in two months), session security (IP-bound tokens), and provider WebSocket integrations with heartbeat keep-alives.',

    'experience.role3.meta':    '2018 – 2019 · Malaysia',
    'experience.role3.title':   'Mobile Engineer',
    'experience.role3.company': 'Hitachi Ebworx',
    'experience.role3.summary': 'Insurance point-of-sale hybrid app; automated the daily QA deployment.',

    // ── Skills ──────────────────────────────────────────────────────────────
    'skills.heading':   'Skills',
    'skills.tier1':     'Core (ships daily)',
    'skills.tier1list': 'TypeScript · NestJS · gRPC / proto-first contracts · MongoDB (aggregation, indexing, Atlas Search) · Redis (data-structure design, cluster) · Temporal · Apache Pulsar · Jest + Testcontainers (real databases, not mocks)',
    'skills.tier2':     'Working',
    'skills.tier2list': 'Java (Flink streaming jobs) · Rust (one full service — Temporal SDK, tonic/prost — pre-production) · Apache Flink (DataStream + SQL, managed) · ClickHouse · Hologres · PostgreSQL · HashiCorp Vault · OpenTelemetry · LangChain / LLM app development',
    'skills.tier3':     'Familiar',
    'skills.tier3list': 'Kafka · Node/Express legacy patterns · Socket.io / Matrix · AngularJS-era stack · Docker · GitHub Actions · Alibaba Cloud (application level)',

    // ── Contact ─────────────────────────────────────────────────────────────
    'contact.heading':   'Get in touch',
    'contact.tagline':   'henrylee_xhfc@hotmail.com · +60 19-413 3366',
    'contact.resumeBtn': 'Resume ↓',
    'contact.copyright': '© 2026 Henry Lee',
  },

  zh: {
    // ── Navigation ──────────────────────────────────────────────────────────
    'nav.work':       '代表作',
    'nav.how':        '思维方式',
    'nav.experience': '工作经历',
    'nav.skills':     '技能',
    'nav.contact':    '联系我',
    'nav.resume':     '简历 ↓',
    'nav.demos':      '演示',

    // ── Hero ────────────────────────────────────────────────────────────────
    'hero.tagline':     '后端团队负责人',
    'hero.positioning': '我设计并交付支撑 30 万+ DAU 真金白银交易平台的系统——从遗留单体到现代微服务，从需求到生产。',
    'hero.ctaContact':  '联系我',
    'hero.ctaResume':   '下载简历',

    // ── Signature Work ──────────────────────────────────────────────────────
    'sig.heading': '代表作',

    // ── How I Think ─────────────────────────────────────────────────────────
    'how.heading': '思维方式',
    'how.p1.title': '先定价风险，再定价工作。',
    'how.p1.proof': '第一个问题从来不是"要多久"——而是"错了谁痛、痛多大？"失败成本决定工程投入：资金路径模块内置幂等、分阶段上线、上线前索引审查；外观功能则追求速度。',
    'how.p2.title': '为下一次变更设计，而不是这一次交付。',
    'how.p2.proof': '这个平台的需求每周都在变。每次设计评审我都会问：哪些部分业务以后想调？那些就做成配置，不是代码。功能需求应该变成运维操作，不是发版。',
    'how.p3.title': '按归属拆解，不是按工单拆解。',
    'how.p3.proof': '大目标沿着模块边界拆，带明确契约——先定 proto，再并行开发。每个工程师 end-to-end 负责一个领域；一个机动位吸收突发。人是通过 ownership 成长的，不是通过接任务。',
    'how.p4.title': '用证据决策，带退路上线。',
    'how.p4.proof': '重大技术选择靠 benchmark 和 POC，不靠意见——每次迁移都带逃生舱。如果量不了或回滚不了，就还没到决定的时候。',
    'how.p5.title': '把工作变成杠杆。',
    'how.p5.proof': '修一个 bug 是成本；把 bug 变成手册或 bot 是资产。做两次的东西就变成工具：集成 SDK、事故手册、全团队在用的 AI 排障 bot。',

    // ── Demos ───────────────────────────────────────────────────────────────
    'demos.heading': '演示与工具',

    // ── Experience ──────────────────────────────────────────────────────────
    'experience.heading': '工作经历',

    'experience.role1.meta':    '2026 – 至今 · Alor Setar, Malaysia',
    'experience.role1.title':   '团队负责人，后端平台',
    'experience.role1.company': 'SN Soft Sdn Bhd',
    'experience.role1.summary': '1 名高级 + 3 名中级工程师，横跨四个模块域，双栈（遗留单体 + 微服务）加第三方 provider 对接。跨团队需求的架构把关人；通过 ownership 和梯度挑战培养工程师——三个 junior 培养到能独立运营整个生产平台，包括跟运营谈需求。一个机动位随时补到需要的地方——跟我当年的成长路径一样。',

    'experience.role2.meta':    '2019.12 – 2026 · 7 年 · Malaysia',
    'experience.role2.title':   '后端工程师 → 代理技术负责人',
    'experience.role2.company': 'SN Soft Sdn Bhd',
    'experience.role2.summary': '七年，2,000+ 合并 PR，从遗留平台全栈到开拓新栈。案例之外的亮点：加固提款流程（双重待审防止、可取消状态、自动审核条件）、C2C 订单匹配嫁接到工作流状态机（两个月 50+ PR）、会话安全（IP 绑定 token）、以及带心跳保活的 provider WebSocket 集成。',

    'experience.role3.meta':    '2018 – 2019 · Malaysia',
    'experience.role3.title':   '移动端工程师',
    'experience.role3.company': 'Hitachi Ebworx',
    'experience.role3.summary': '保险 POS 混合应用；自动化了每日 QA 部署。',

    // ── Skills ──────────────────────────────────────────────────────────────
    'skills.heading':   '技能',
    'skills.tier1':     '核心（日常交付）',
    'skills.tier1list': 'TypeScript · NestJS · gRPC / proto-first 契约 · MongoDB（聚合、索引、Atlas Search）· Redis（数据结构设计、集群）· Temporal · Apache Pulsar · Jest + Testcontainers（真实数据库，非 mock）',
    'skills.tier2':     '熟练',
    'skills.tier2list': 'Java（Flink 流任务）· Rust（一个完整服务——Temporal SDK、tonic/prost——预生产）· Apache Flink（DataStream + SQL、托管）· ClickHouse · Hologres · PostgreSQL · HashiCorp Vault · OpenTelemetry · LangChain / LLM 应用开发',
    'skills.tier3':     '了解',
    'skills.tier3list': 'Kafka · Node/Express 遗留模式 · Socket.io / Matrix · AngularJS 时代技术栈 · Docker · GitHub Actions · Alibaba Cloud（应用层）',

    // ── Contact ─────────────────────────────────────────────────────────────
    'contact.heading':   '联系我',
    'contact.tagline':   'henrylee_xhfc@hotmail.com · +60 19-413 3366',
    'contact.resumeBtn': '简历 ↓',
    'contact.copyright': '© 2026 Henry Lee',
  },
};

// ── Apply i18n to all [data-i18n] elements ───────────────────────────────
window.applyI18n = function () {
  var lang = document.documentElement.lang || 'en';
  var dict = window.I18N[lang] || window.I18N.en;
  document.querySelectorAll('[data-i18n]').forEach(function (el) {
    var key = el.getAttribute('data-i18n');
    if (dict[key] !== undefined) {
      el.textContent = dict[key];
    }
  });
};

// Auto-apply on DOMContentLoaded
document.addEventListener('DOMContentLoaded', window.applyI18n);
