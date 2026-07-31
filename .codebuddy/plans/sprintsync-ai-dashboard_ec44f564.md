---
name: sprintsync-ai-dashboard
overview: 从零构建 SprintSync AI 的 Next.js + Express 全栈 SaaS 仪表盘，包含完整的左侧导航、顶部 Header、Repository Overview、AI Agent Panel、Suggested Documentation Update、Team Progress 和 Activity Timeline 模块。
design:
  architecture:
    framework: react
    component: shadcn
  styleKeywords:
    - Minimal B2B SaaS
    - Engineering Dashboard
    - Linear-inspired
    - White Background
    - Subtle Gray Cards
    - Rounded Corners
    - Professional Typography
    - GitHub Aesthetic
    - Monospace Accents
    - Green CTA
  fontSystem:
    fontFamily: DM Sans
    heading:
      size: 18px
      weight: 600
    subheading:
      size: 14px
      weight: 500
    body:
      size: 14px
      weight: 400
  colorSystem:
    primary:
      - "#111827"
      - "#16A34A"
      - "#3B82F6"
    background:
      - "#F8F9FA"
      - "#FFFFFF"
      - "#FAFAFA"
      - "#F3F4F6"
    text:
      - "#111827"
      - "#6B7280"
      - "#9CA3AF"
    functional:
      - "#22C55E"
      - "#EF4444"
      - "#F59E0B"
      - "#3B82F6"
      - "#24292f"
      - "#000000"
todos:
  - id: init-monorepo
    content: 初始化 Monorepo 结构，创建根 package.json、pnpm-workspace.yaml 及 apps/web（Next.js）和 apps/api（Express）基础配置文件
    status: completed
  - id: express-api
    content: 构建 Express API 服务：入口文件、dashboard/suggestions/activity/repos 四个路由及完整 mockData 数据层
    status: completed
    dependencies:
      - init-monorepo
  - id: layout-components
    content: 使用 [skill:frontend-design] 实现 Next.js 根布局、Sidebar 导航组件和 Header 组件（含 GitHub/Notion 品牌图标、Agent 状态指示器）
    status: completed
    dependencies:
      - init-monorepo
  - id: dashboard-panels
    content: 使用 [skill:frontend-design] 实现主看板四个核心 Panel：RepoOverview、AIAgentPanel（含 Recharts 置信度图）、TeamProgress（含 Sprint 环形图）、ActivityTimeline
    status: completed
    dependencies:
      - layout-components
      - express-api
  - id: suggestion-card
    content: 使用 [skill:ui-ux-pro-max] 实现 SuggestedDocUpdate 卡片：进度对比展示、AI 推理区域、文件列表及 Approve/Reject/Edit 完整交互逻辑
    status: completed
    dependencies:
      - dashboard-panels
---

## 用户需求

构建 **SprintSync AI** — 一款面向软件团队的 AI 工程运营 Agent SaaS 仪表盘，核心功能是自动同步 GitHub 开发进度与 Notion 文档。目标用户为工程经理、技术负责人和软件团队。

## 产品概览

全栈应用，前端采用 Next.js，后端采用 Node.js Express。设计语言 clean、modern、minimal，参考 Linear / GitHub / Notion 的 B2B SaaS 美学：白色背景 + 微灰卡片 + 圆角 + 专业排版。

## 核心功能模块

### 左侧导航栏

- 品牌 Logo（SprintSync AI）
- 导航菜单：Dashboard / Repositories / Tasks / AI Suggestions / Activity / Integrations / Settings

### 顶部 Header

- 已连接 GitHub 仓库（仓库名 + 分支）
- 已连接 Notion Workspace（工作区名称 + 图标）
- AI Agent 状态指示器（Running / Idle / Error 三态）
- 通知铃铛（带未读徽章）
- 用户头像 + 下拉菜单

### 主看板（Main Dashboard）

**Repository Overview**

- 最新 commits 列表（commit message、作者、时间、hash）
- 近期 Pull Requests（标题、状态、作者、时间）
- 仓库健康度评分（代码覆盖率、CI 状态、未关闭 PR 数）

**AI Agent Panel**

- 当前分析状态（动态进度条 / 状态 badge）
- 已分析文件数量
- 置信度评分（百分比 + 可视化）
- 最近同步时间

**Suggested Documentation Update 卡片**

- 关联任务名称
- 现有文档进度（Existing Progress）
- 建议更新后的进度（Suggested Progress）
- AI 推理说明（AI Reasoning）
- 相关文件列表
- 操作按钮：Approve / Reject / Edit before approving

**Team Progress**

- Sprint 完成百分比（环形进度图）
- Open tasks 数量
- 最近更新的任务列表
- 被阻塞任务列表（带阻塞标记）

**Activity Timeline**

- 时间线事件类型：Commit received → AI analyzed repository → Documentation suggestion created → User approved update → Notion synchronized
- 每条事件含图标、描述、时间戳

## 技术栈

| 层级 | 技术 |
| --- | --- |
| 前端框架 | Next.js 14 (App Router) + TypeScript |
| 样式 | Tailwind CSS v3 |
| UI 组件库 | shadcn/ui |
| 图表 | Recharts |
| 图标 | Lucide React + 自定义 GitHub/Notion SVG |
| 动画 | Framer Motion |
| 后端 | Node.js + Express.js + TypeScript |
| 数据模拟 | Mock JSON（无需真实 DB，Seed 数据） |
| 包管理 | pnpm（monorepo） |


## 实现思路

采用 **Monorepo** 结构，`apps/web`（Next.js）和 `apps/api`（Express）分离部署。前端通过 Next.js API Routes 代理或直接调用 Express REST API 获取 mock 数据，完整渲染仪表盘所有模块。

所有仪表盘数据通过 Express mock API 返回，Next.js 使用 `fetch` + `server components` 在服务端获取数据，同时保留交互性 AI Suggestion 卡片（Approve/Reject/Edit）为 client component，确保 UX 流畅。

**关键设计决策：**

- 使用 shadcn/ui 作为基础组件，保证与 Linear/Notion 风格一致的 B2B 专业感
- Sidebar 固定宽度 240px，使用 `next/navigation` activeLink 高亮
- AI Suggestion 卡片的 Approve/Reject/Edit 状态通过 React useState 管理，乐观更新 UI
- Activity Timeline 纯前端渲染，mock 数据包含5种事件类型的完整状态机
- 置信度、Sprint 进度使用 Recharts RadialBarChart 可视化

## 架构设计

```mermaid
graph TB
    subgraph "Frontend (Next.js 14)"
        A[App Router Layout] --> B[Left Sidebar]
        A --> C[Top Header]
        A --> D[Dashboard Page]
        D --> E[RepoOverview]
        D --> F[AIAgentPanel]
        D --> G[SuggestedDocUpdate]
        D --> H[TeamProgress]
        D --> I[ActivityTimeline]
    end

    subgraph "Backend (Express API)"
        J[/api/dashboard] --> K[Mock Data Layer]
        L[/api/suggestions] --> K
        M[/api/activity] --> K
        N[/api/repos] --> K
    end

    D -->|fetch| J
    G -->|POST approve/reject| L
    I -->|fetch| M
```

## 目录结构

```
sprintsync/
├── package.json                    # [NEW] 根 workspace pnpm 配置
├── pnpm-workspace.yaml             # [NEW] monorepo workspace 声明
│
├── apps/
│   ├── web/                        # Next.js 前端
│   │   ├── package.json            # [NEW] Next.js 依赖
│   │   ├── next.config.ts          # [NEW] Next.js 配置，含 API 代理
│   │   ├── tailwind.config.ts      # [NEW] Tailwind + shadcn 主题配置
│   │   ├── components.json         # [NEW] shadcn/ui 配置
│   │   └── src/
│   │       ├── app/
│   │       │   ├── layout.tsx      # [NEW] 根布局，Sidebar + Header 框架
│   │       │   ├── page.tsx        # [NEW] Dashboard 主页，组合所有 Panel
│   │       │   └── globals.css     # [NEW] 全局样式，CSS 变量
│   │       ├── components/
│   │       │   ├── layout/
│   │       │   │   ├── Sidebar.tsx         # [NEW] 左侧导航：Logo + 7 个菜单项，activeLink 高亮
│   │       │   │   └── Header.tsx          # [NEW] 顶部 Header：GitHub/Notion 连接状态、Agent 状态、通知、用户头像
│   │       │   ├── dashboard/
│   │       │   │   ├── RepoOverview.tsx    # [NEW] 仓库概览：commits 列表、PR 列表、健康度评分卡
│   │       │   │   ├── AIAgentPanel.tsx    # [NEW] AI Agent 状态面板：分析进度、文件数、置信度 RadialBar、同步时间
│   │       │   │   ├── SuggestedDocUpdate.tsx  # [NEW] 建议文档更新卡（client component）：任务关联、进度对比、AI 推理、文件列表、三个操作按钮
│   │       │   │   ├── TeamProgress.tsx    # [NEW] 团队进度：Sprint 环形图、open/blocked tasks、最近更新列表
│   │       │   │   └── ActivityTimeline.tsx # [NEW] 活动时间线：5种事件类型，图标 + 描述 + 时间戳
│   │       │   └── ui/
│   │       │       ├── StatusBadge.tsx     # [NEW] 通用状态 badge（Running/Idle/Error/Open/Blocked）
│   │       │       ├── ConfidenceBar.tsx   # [NEW] 置信度可视化条形组件
│   │       │       └── GitHubIcon.tsx      # [NEW] GitHub SVG 品牌图标
│   │       │       └── NotionIcon.tsx      # [NEW] Notion SVG 品牌图标
│   │       └── lib/
│   │           ├── api.ts          # [NEW] fetch 封装，调用 Express API
│   │           └── types.ts        # [NEW] 全局 TypeScript 类型定义
│   │
│   └── api/                        # Express 后端
│       ├── package.json            # [NEW] Express 依赖（express, cors, typescript）
│       ├── tsconfig.json           # [NEW] TypeScript 配置
│       └── src/
│           ├── index.ts            # [NEW] Express 入口，CORS 配置，路由挂载
│           ├── routes/
│           │   ├── dashboard.ts    # [NEW] GET /api/dashboard — 返回仪表盘汇总数据
│           │   ├── suggestions.ts  # [NEW] GET /api/suggestions，POST /api/suggestions/:id/approve|reject
│           │   ├── activity.ts     # [NEW] GET /api/activity — 返回时间线事件列表
│           │   └── repos.ts        # [NEW] GET /api/repos — 返回仓库列表和健康度
│           └── data/
│               └── mockData.ts     # [NEW] 所有 mock 数据：commits、PRs、suggestions、activity、team progress
```

## 实现要点

1. **Mock 数据驱动**：Express 返回真实结构的 JSON（commits 含 hash/author/message/time，PRs 含 state/reviewers，suggestions 含 reasoning/files/diff），前端原样渲染，保证视觉真实感。

2. **SuggestedDocUpdate 交互**：Approve 后更新本地状态显示 "Approved" badge 并禁用按钮；Edit 打开内联编辑 textarea 修改 suggested progress 内容；Reject 显示 strikethrough 效果，符合工程师习惯的 UX 模式。

3. **Agent 状态轮询**：AIAgentPanel 使用 `setInterval` 每 30s 轮询一次 `/api/dashboard` 中的 agent status，模拟实时感。

4. **设计一致性**：所有卡片使用 `border border-gray-100 rounded-xl shadow-sm bg-white` 统一样式；Sidebar active item 使用 `bg-gray-100 text-gray-900 font-medium`；GitHub 使用 `#24292f` 品牌色，Notion 使用 `#000000` 品牌色。

5. **TypeScript 类型共享**：`apps/web/src/lib/types.ts` 定义所有接口（Commit、PullRequest、Suggestion、ActivityEvent、TeamProgress），前后端对齐。

## 设计风格

**定位**：专业 B2B SaaS 工程仪表盘，灵感来自 Linear、GitHub、Notion 的极简主义。

**整体布局**：三栏式 — 固定 240px 左侧导航 + 固定顶部 Header（64px）+ 主内容区 grid 布局。主内容区使用 CSS Grid 实现两列响应式排列：左侧宽列（Repository Overview + Suggested Doc Update + Activity Timeline），右侧窄列（AI Agent Panel + Team Progress）。

**视觉语言**：

- 白色主背景 `#FFFFFF`，微灰页面底色 `#F8F9FA`
- 所有卡片：白底 + `1px #E5E7EB` 边框 + `8px` 圆角 + 轻微投影 `shadow-sm`
- Sidebar 背景 `#FAFAFA`，右侧 `1px #E5E7EB` 分隔线
- 导航 active 状态：`#F3F4F6` 背景 + `#111827` 文字
- 强调色仅用于 CTA 按钮（Approve 按钮使用 `#16A34A` 绿色）和 Agent 状态指示（Running 使用 `#22C55E` 动态脉冲点）

**排版**：

- Headings：`DM Sans` — 工程感强，现代且不失专业
- Body：`IBM Plex Mono`（commit hash、文件路径）+ `DM Sans`（常规文本）
- 卡片标题 14px 500 weight `#6B7280`，内容 14-15px 400/500 `#111827`

**微交互**：

- Approve/Reject 按钮 hover 有 scale(1.01) + 颜色加深过渡（150ms ease）
- Sidebar 菜单 hover 背景淡入（100ms）
- Agent Running 状态显示 CSS 脉冲动画绿点
- Activity Timeline 事件图标使用浅色背景圆形容器，与线条连接

**GitHub / Notion 品牌**：

- GitHub Octocat SVG 图标 + `#24292f` 配色，出现在 Header 仓库连接处和 commit 列表
- Notion 黑色方块 SVG 图标，出现在 Header Workspace 连接处和 Activity Timeline 的 "Notion synchronized" 事件

## 页面规划

**Page 1 — Dashboard（主看板）**：

- Block 1：顶部 Header（GitHub 仓库连接 + Notion Workspace + Agent 状态 + 通知 + 头像）
- Block 2：Repository Overview 卡片（左栏 commits + PR 列表 + 健康度 badges）
- Block 3：AI Agent Panel 卡片（右栏，状态 + RadialBar 置信度 + 文件数 + 同步时间）
- Block 4：Suggested Documentation Update 卡片（左栏，全宽，diff 对比 + 操作按钮）
- Block 5：Team Progress 卡片（右栏，Sprint 圆环图 + tasks 列表）
- Block 6：Activity Timeline 卡片（底部全宽，水平或垂直时间线）

## 使用的 Agent 扩展

### Skill

- **frontend-design**
- Purpose：生成高质量、生产级的前端界面代码，包含所有仪表盘组件（Sidebar、Header、RepoOverview、AIAgentPanel、SuggestedDocUpdate、TeamProgress、ActivityTimeline）的完整实现，并确保设计风格与 Linear/GitHub/Notion 对齐
- Expected outcome：输出完整、可运行的 Next.js 组件代码，视觉上专业美观，符合 B2B SaaS 设计标准，包含所有交互逻辑（Approve/Reject/Edit）和 mock 数据渲染

- **ui-ux-pro-max**
- Purpose：校验和优化 UI/UX 细节，确保组件库（shadcn/ui）集成正确，颜色系统、间距、字体排版一致，并对 Recharts 可视化组件（RadialBar、CircularProgress）进行最优配置
- Expected outcome：所有 shadcn/ui 组件正确配置，Tailwind 主题与设计规范对齐，图表组件渲染正确