# UI 重新设计实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 重新设计废水监测系统 UI，采用企业级监控工具风格（左侧导航 + 顶部栏），保持所有现有功能

**Architecture:** 渐进式迁移 - 先修改布局和样式（阶段1），再更新交互逻辑（阶段2），最后优化体验（阶段3）

**Tech Stack:** HTML5, CSS3, Vanilla JavaScript, Chart.js, Axios

---

## 文件结构

| 文件 | 职责 | 修改类型 |
|-----|------|---------|
| `middleware/static/index.html` | 页面结构和布局 | 重构 |
| `middleware/static/css/styles.css` | 全局样式和组件样式 | 重写 |
| `middleware/static/js/app.js` | 应用逻辑和交互 | 修改 |
| `middleware/static/js/charts.js` | 图表渲染逻辑 | 小修改 |
| `middleware/static/js/monitoring.js` | 监控面板逻辑 | 修改 |

---

## 阶段1：布局和样式重构（P0）

### Task 1: 更新 CSS 变量和配色方案

**Files:**
- Modify: `middleware/static/css/styles.css`

**目标:** 实现新的企业级蓝色系配色方案

- [ ] **Step 1: 在 styles.css 顶部添加 CSS 变量定义**

在 `:root` 选择器中添加所有配色变量：

```css
:root {
    /* 主色 - 蓝色系 */
    --primary: #2563eb;
    --primary-dark: #1d4ed8;
    --primary-light: #60a5fa;
    --primary-bg: #eff6ff;

    /* 中性色 */
    --bg-primary: #ffffff;
    --bg-secondary: #f1f5f9;
    --bg-tertiary: #e2e8f0;
    --border: #cbd5e1;

    /* 文本色 */
    --text-primary: #0f172a;
    --text-secondary: #64748b;
    --text-tertiary: #94a3b8;

    /* 导航栏 */
    --nav-bg: #1e293b;
    --nav-hover: #334155;
    --nav-active: #2563eb;

    /* 状态色 */
    --success: #22c55e;
    --warning: #f59e0b;
    --danger: #ef4444;
    --info: #3b82f6;

    /* 字体 */
    --font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    --font-xs: 12px;
    --font-sm: 14px;
    --font-base: 16px;
    --font-lg: 18px;
    --font-xl: 24px;
    --font-2xl: 32px;
}
```

- [ ] **Step 2: 在浏览器中验证**

打开 `http://localhost:8080`，按 F12 打开开发者工具，在 Console 中输入：
```javascript
getComputedStyle(document.documentElement).getPropertyValue('--primary')
```
预期输出: `"#2563eb"`

- [ ] **Step 3: 提交变更**

```bash
git add middleware/static/css/styles.css
git commit -m "style: add CSS variables for new color scheme"
```

---

### Task 2: 重构 HTML 结构为左侧导航布局

**Files:**
- Modify: `middleware/static/index.html`

**目标:** 将顶部标签页布局改为左侧导航 + 顶部栏 + 主内容区布局

- [ ] **Step 1: 备份当前 index.html**

```bash
cp middleware/static/index.html middleware/static/index.html.backup
```

- [ ] **Step 2: 重写 HTML 结构**

将 `<body>` 内的内容替换为新布局：

```html
<body>
    <div class="app-layout">
        <!-- 左侧导航栏 -->
        <aside class="sidebar">
            <div class="sidebar-header">
                <div class="logo-icon">🏭</div>
                <div class="logo-text" style="display: none;">监测系统</div>
            </div>
            <nav class="sidebar-nav">
                <a href="#" class="nav-item active" data-panel="query">
                    <span class="nav-icon">🔍</span>
                    <span class="nav-text">智能查询</span>
                </a>
                <a href="#" class="nav-item" data-panel="monitoring">
                    <span class="nav-icon">📊</span>
                    <span class="nav-text">实时监控</span>
                </a>
                <a href="#" class="nav-item" data-panel="analysis">
                    <span class="nav-icon">📈</span>
                    <span class="nav-text">分析报告</span>
                </a>
                <a href="#" class="nav-item" data-panel="settings">
                    <span class="nav-icon">⚙️</span>
                    <span class="nav-text">系统设置</span>
                </a>
            </nav>
            <div class="sidebar-footer">
                <button class="sidebar-toggle" id="sidebar-toggle">
                    <span>«</span>
                </button>
            </div>
        </aside>

        <!-- 主内容区 -->
        <div class="main-wrapper">
            <!-- 顶部综合栏 -->
            <header class="top-bar">
                <div class="top-bar-left">
                    <h1 class="page-title">智能查询</h1>
                </div>
                <div class="top-bar-center">
                    <div class="search-box">
                        <span class="search-icon">🔍</span>
                        <input type="text" class="search-input" placeholder="搜索查询、指标、报告...">
                    </div>
                </div>
                <div class="top-bar-right">
                    <button class="icon-btn" id="alert-btn">
                        <span>🔔</span>
                        <span class="badge" id="alert-badge" style="display: none;">0</span>
                    </button>
                    <div class="user-menu">
                        <span class="user-avatar">👤</span>
                        <span class="user-name">用户</span>
                    </div>
                </div>
            </header>

            <!-- 内容区 -->
            <main class="main-content">
                <!-- 智能查询面板 -->
                <section id="query-panel" class="content-panel active">
                    <!-- 保持原有查询内容 -->
                    <div class="query-section">
                        <div class="query-input-wrapper">
                            <textarea id="query-input" placeholder="请输入查询问题...

示例查询：
• 过去24小时pH和COD之间的相关性怎么样？
• 检测最近一周的数据异常
• 分析氨氮和总磷的变化趋势"></textarea>
                            <div class="query-actions">
                                <button id="query-btn" class="btn btn-primary">
                                    <span class="btn-icon">🔍</span>
                                    <span class="btn-text">开始分析</span>
                                </button>
                                <button id="clear-btn" class="btn btn-secondary">
                                    <span class="btn-text">清空</span>
                                </button>
                            </div>
                        </div>

                        <!-- 查询状态 -->
                        <div id="query-status" class="status-box hidden">
                            <div class="status-indicator">
                                <div class="spinner"></div>
                                <span class="status-text">正在分析中...</span>
                            </div>
                            <div class="progress-steps">
                                <div class="step" data-step="parse">
                                    <span class="step-icon">📝</span>
                                    <span class="step-text">解析意图</span>
                                </div>
                                <div class="step" data-step="fetch">
                                    <span class="step-icon">📊</span>
                                    <span class="step-text">获取数据</span>
                                </div>
                                <div class="step" data-step="analyze">
                                    <span class="step-icon">🤖</span>
                                    <span class="step-text">智能分析</span>
                                </div>
                                <div class="step" data-step="report">
                                    <span class="step-icon">📋</span>
                                    <span class="step-text">生成报告</span>
                                </div>
                            </div>
                        </div>

                        <!-- 查询结果 -->
                        <div id="query-result" class="result-box hidden">
                            <div class="result-header">
                                <h3>📊 分析结果</h3>
                            </div>
                            <div class="result-content">
                                <div class="result-summary" id="result-summary"></div>
                                <div class="result-charts" id="result-charts"></div>
                            </div>
                        </div>
                    </div>
                </section>

                <!-- 实时监控面板 -->
                <section id="monitoring-panel" class="content-panel">
                    <div class="monitoring-section">
                        <!-- 指标卡片网格 -->
                        <div class="metrics-grid">
                            <div class="metric-card">
                                <div class="metric-title">进水pH</div>
                                <div class="metric-value" id="metric-influent-ph">--</div>
                                <div class="metric-trend">→</div>
                            </div>
                            <div class="metric-card">
                                <div class="metric-title">出水COD</div>
                                <div class="metric-value" id="metric-effluent-cod">--</div>
                                <div class="metric-trend">→</div>
                            </div>
                            <div class="metric-card">
                                <div class="metric-title">进水TN</div>
                                <div class="metric-value" id="metric-influent-tn">--</div>
                                <div class="metric-trend">→</div>
                            </div>
                            <div class="metric-card">
                                <div class="metric-title">异常数</div>
                                <div class="metric-value" id="metric-anomalies">--</div>
                                <div class="metric-trend" id="metric-status">⚠️</div>
                            </div>
                        </div>

                        <!-- Grafana 容器 -->
                        <div class="grafana-header">
                            <h2>📊 实时监控仪表板</h2>
                            <button class="btn btn-grafana" onclick="window.open('http://localhost:3000/goto/cfo42tuskodtsf?orgId=1', '_blank')">
                                <span class="btn-icon">📈</span>
                                <span class="btn-text">打开Grafana完整仪表板</span>
                            </button>
                        </div>

                        <div class="grafana-container" id="grafana-container">
                            <iframe id="grafana-iframe"
                                    src="http://localhost:3000/goto/cfo42tuskodtsf?orgId=1&embed=true"
                                    frameborder="0"
                                    allowtransparency="true">
                            </iframe>
                            <div class="grafana-fallback">
                                <p>无法加载Grafana仪表板</p>
                                <button class="btn btn-primary" onclick="window.open('http://localhost:3000/goto/cfo42tuskodtsf?orgId=1', '_blank')">
                                    在新窗口打开
                                </button>
                            </div>
                        </div>

                        <!-- 备用图表 -->
                        <div class="charts-grid">
                            <div class="chart-container">
                                <canvas id="realtime-chart"></canvas>
                            </div>
                        </div>
                    </div>
                </section>

                <!-- 分析报告面板 -->
                <section id="analysis-panel" class="content-panel">
                    <div class="analysis-section">
                        <div class="analysis-header">
                            <h2>📈 最近分析报告</h2>
                            <div class="analysis-filters">
                                <select class="filter-select">
                                    <option>今天</option>
                                    <option>本周</option>
                                    <option selected>本月</option>
                                </select>
                                <input type="text" class="search-input" placeholder="搜索报告..." style="width: 200px;">
                            </div>
                        </div>
                        <div id="analysis-list" class="analysis-list">
                            <div class="loading">加载中...</div>
                        </div>
                    </div>
                </section>

                <!-- 系统设置面板（新增，暂留空） -->
                <section id="settings-panel" class="content-panel">
                    <div class="settings-section">
                        <h2>⚙️ 系统设置</h2>
                        <p style="color: var(--text-secondary);">设置功能开发中...</p>
                    </div>
                </section>
            </main>
        </div>
    </div>

    <!-- 告警面板（右侧滑出） -->
    <div class="alert-overlay" id="alert-overlay"></div>
    <aside class="alert-panel" id="alert-panel">
        <div class="alert-panel-header">
            <h3>🔔 告警通知</h3>
            <button class="close-btn" id="alert-close">×</button>
        </div>
        <div class="alert-panel-content" id="alert-list">
            <div class="empty-state">暂无告警</div>
        </div>
    </aside>

    <script src="/js/app.js"></script>
    <script src="/js/charts.js"></script>
    <script src="/js/monitoring.js"></script>
</body>
```

- [ ] **Step 3: 验证 HTML 结构**

打开 `http://localhost:8080`，检查：
1. 左侧导航栏可见
2. 顶部栏可见
3. 三个面板内容存在
4. 使用 F12 检查无 HTML 解析错误

- [ ] **Step 4: 提交变更**

```bash
git add middleware/static/index.html
git commit -m "refactor: restructure HTML layout with sidebar navigation"
```

---

### Task 3: 编写新的 CSS 样式

**Files:**
- Modify: `middleware/static/css/styles.css`

**目标:** 实现新布局的完整样式

- [ ] **Step 1: 添加基础重置和布局样式**

在 styles.css 顶部添加（在 `:root` 变量之后）：

```css
/* 基础重置 */
* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

body {
    font-family: var(--font-family);
    font-size: var(--font-base);
    color: var(--text-primary);
    background: var(--bg-secondary);
    line-height: 1.5;
}

/* 布局容器 */
.app-layout {
    display: flex;
    height: 100vh;
    overflow: hidden;
}

/* 左侧导航栏 */
.sidebar {
    width: 64px;
    background: var(--nav-bg);
    display: flex;
    flex-direction: column;
    transition: width 200ms ease-out;
    flex-shrink: 0;
}

.sidebar.expanded {
    width: 240px;
}

.sidebar-header {
    height: 56px;
    display: flex;
    align-items: center;
    justify-content: center;
    border-bottom: 1px solid rgba(255,255,255,0.1);
    padding: 0 16px;
}

.logo-icon {
    font-size: 24px;
}

.logo-text {
    margin-left: 12px;
    font-size: 14px;
    font-weight: 600;
    color: white;
}

/* 导航项 */
.sidebar-nav {
    flex: 1;
    padding: 16px 0;
}

.nav-item {
    display: flex;
    align-items: center;
    padding: 12px 20px;
    color: var(--nav-text);
    text-decoration: none;
    transition: all 200ms ease-out;
    position: relative;
}

.nav-item:hover {
    background: var(--nav-hover);
    color: white;
}

.nav-item.active {
    color: white;
    background: rgba(37, 99, 235, 0.1);
}

.nav-item.active::before {
    content: '';
    position: absolute;
    left: 0;
    top: 0;
    bottom: 0;
    width: 3px;
    background: var(--primary);
}

.nav-icon {
    font-size: 20px;
    flex-shrink: 0;
}

.nav-text {
    margin-left: 12px;
    font-size: 14px;
    white-space: nowrap;
    opacity: 0;
}

.sidebar.expanded .nav-text {
    opacity: 1;
}

.sidebar-footer {
    height: 56px;
    display: flex;
    align-items: center;
    justify-content: center;
    border-top: 1px solid rgba(255,255,255,0.1);
}

.sidebar-toggle {
    background: none;
    border: none;
    color: var(--nav-text);
    font-size: 18px;
    cursor: pointer;
    padding: 8px;
}

.sidebar-toggle:hover {
    color: white;
}

/* 主内容区 */
.main-wrapper {
    flex: 1;
    display: flex;
    flex-direction: column;
    overflow: hidden;
}

/* 顶部栏 */
.top-bar {
    height: 56px;
    background: var(--bg-primary);
    border-bottom: 1px solid var(--border);
    display: flex;
    align-items: center;
    padding: 0 24px;
    gap: 24px;
    flex-shrink: 0;
}

.top-bar-left {
    flex: 1;
}

.page-title {
    font-size: 20px;
    font-weight: 600;
    color: var(--text-primary);
}

.top-bar-center {
    flex: 1;
}

.search-box {
    display: flex;
    align-items: center;
    background: var(--bg-secondary);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 0 12px;
    max-width: 400px;
    width: 100%;
}

.search-box:focus-within {
    border-color: var(--primary);
}

.search-icon {
    font-size: 16px;
    margin-right: 8px;
}

.search-input {
    flex: 1;
    border: none;
    background: none;
    padding: 8px 0;
    font-size: 14px;
    outline: none;
}

.top-bar-right {
    display: flex;
    align-items: center;
    gap: 16px;
}

.icon-btn {
    position: relative;
    background: none;
    border: none;
    font-size: 20px;
    cursor: pointer;
    padding: 8px;
    border-radius: 8px;
}

.icon-btn:hover {
    background: var(--bg-secondary);
}

.badge {
    position: absolute;
    top: 4px;
    right: 4px;
    background: var(--danger);
    color: white;
    font-size: 10px;
    padding: 2px 6px;
    border-radius: 10px;
    min-width: 16px;
    text-align: center;
}

.user-menu {
    display: flex;
    align-items: center;
    gap: 8px;
    cursor: pointer;
    padding: 4px 8px;
    border-radius: 8px;
}

.user-menu:hover {
    background: var(--bg-secondary);
}

/* 内容区 */
.main-content {
    flex: 1;
    overflow-y: auto;
    padding: 24px;
}

.content-panel {
    display: none;
}

.content-panel.active {
    display: block;
}

/* 卡片通用样式 */
.metric-card,
.chart-container,
.query-section,
.monitoring-section,
.analysis-section {
    background: var(--bg-primary);
    border-radius: 8px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    padding: 16px;
}

/* 指标卡片网格 */
.metrics-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 16px;
    margin-bottom: 24px;
}

.metric-card {
    text-align: center;
}

.metric-title {
    font-size: 12px;
    color: var(--text-secondary);
    margin-bottom: 8px;
}

.metric-value {
    font-size: 32px;
    font-weight: 700;
    color: var(--primary);
    margin-bottom: 4px;
}

.metric-trend {
    font-size: 14px;
    color: var(--text-secondary);
}

/* 告警面板 */
.alert-overlay {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: rgba(0,0,0,0.5);
    opacity: 0;
    visibility: hidden;
    transition: all 200ms ease-in;
    z-index: 1000;
}

.alert-overlay.show {
    opacity: 1;
    visibility: visible;
}

.alert-panel {
    position: fixed;
    top: 0;
    right: 0;
    bottom: 0;
    width: 320px;
    background: var(--bg-primary);
    transform: translateX(100%);
    transition: transform 300ms ease-out;
    z-index: 1001;
    display: flex;
    flex-direction: column;
}

.alert-panel.show {
    transform: translateX(0);
}

.alert-panel-header {
    height: 56px;
    border-bottom: 1px solid var(--border);
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0 16px;
}

.alert-panel-header h3 {
    font-size: 16px;
    font-weight: 600;
}

.close-btn {
    background: none;
    border: none;
    font-size: 24px;
    cursor: pointer;
    padding: 4px;
}

.alert-panel-content {
    flex: 1;
    overflow-y: auto;
    padding: 16px;
}

/* 响应式 */
@media (max-width: 1200px) {
    .metrics-grid {
        grid-template-columns: repeat(2, 1fr);
    }
}

@media (max-width: 768px) {
    .sidebar {
        width: 0;
    }
    
    .top-bar-center {
        display: none;
    }
    
    .metrics-grid {
        grid-template-columns: 1fr;
    }
    
    .main-content {
        padding: 16px;
    }
}
```

- [ ] **Step 2: 验证样式效果**

打开 `http://localhost:8080`，检查：
1. 左侧导航栏是深蓝色
2. 顶部栏白色有边框
3. 卡片白色有阴影
4. 响应式在调整窗口大小时生效

- [ ] **Step 3: 提交变更**

```bash
git add middleware/static/css/styles.css
git commit -m "style: add new layout styles with sidebar navigation"
```

---

### Task 4: 更新导航切换逻辑

**Files:**
- Modify: `middleware/static/js/app.js`

**目标:** 更新导航切换逻辑，适配新的侧边栏导航

- [ ] **Step 1: 找到 handleTabSwitch 函数并修改**

将原有的标签页切换逻辑替换为侧边栏导航逻辑：

找到原函数（约92行）：
```javascript
function handleTabSwitch(e) {
    const tabId = e.target.dataset.tab;
    // ...
}
```

替换为：
```javascript
function handleTabSwitch(e) {
    e.preventDefault();
    const navItem = e.target.closest('.nav-item');
    if (!navItem) return;
    
    const panelId = navItem.dataset.panel;
    if (!panelId) return;

    // 更新导航状态
    document.querySelectorAll('.nav-item').forEach(item => {
        item.classList.remove('active');
    });
    navItem.classList.add('active');

    // 更新面板显示
    document.querySelectorAll('.content-panel').forEach(panel => {
        panel.classList.remove('active');
    });
    
    const targetPanel = document.getElementById(`${panelId}-panel`);
    if (targetPanel) {
        targetPanel.classList.add('active');
    }

    // 更新页面标题
    const titles = {
        'query': '智能查询',
        'monitoring': '实时监控',
        'analysis': '分析报告',
        'settings': '系统设置'
    };
    document.querySelector('.page-title').textContent = titles[panelId] || '监测系统';

    // 如果切换到监控面板，启动监控
    if (panelId === 'monitoring') {
        if (typeof startMonitoring === 'function') {
            startMonitoring();
        }
    }
}
```

- [ ] **Step 2: 更新事件绑定**

找到 DOMContentLoaded 监听器（约27行），更新事件绑定：

将：
```javascript
elements.tabButtons.forEach(btn => {
    btn.addEventListener('click', handleTabSwitch);
});
```

替换为：
```javascript
// 绑定侧边栏导航点击
document.querySelectorAll('.nav-item').forEach(item => {
    item.addEventListener('click', handleTabSwitch);
});

// 侧边栏展开/收起
const sidebarToggle = document.getElementById('sidebar-toggle');
const sidebar = document.querySelector('.sidebar');
sidebarToggle.addEventListener('click', () => {
    sidebar.classList.toggle('expanded');
    // 更新按钮文字
    const span = sidebarToggle.querySelector('span');
    span.textContent = sidebar.classList.contains('expanded') ? '»' : '«';
});
```

- [ ] **Step 3: 测试导航切换**

打开 `http://localhost:8080`：
1. 点击左侧导航项，面板应该切换
2. 点击收起/展开按钮，导航应该收起/展开
3. 页面标题应该随之更新

- [ ] **Step 4: 提交变更**

```bash
git add middleware/static/js/app.js
git commit -m "refactor: update navigation logic for sidebar layout"
```

---

## 阶段2：新增功能实现（P1）

### Task 5: 实现告警面板功能

**Files:**
- Modify: `middleware/static/js/app.js`

**目标:** 实现右侧告警面板的显示和数据加载

- [ ] **Step 1: 添加告警面板显示逻辑**

在 app.js 中添加告警面板相关函数：

```javascript
// 告警面板管理
const alertPanel = {
    overlay: document.getElementById('alert-overlay'),
    panel: document.getElementById('alert-panel'),
    content: document.getElementById('alert-list'),
    closeBtn: document.getElementById('alert-close'),
    
    init() {
        // 点击关闭按钮
        this.closeBtn.addEventListener('click', () => this.hide());
        
        // 点击遮罩关闭
        this.overlay.addEventListener('click', () => this.hide());
        
        // 点击告铃按钮显示面板
        const alertBtn = document.getElementById('alert-btn');
        if (alertBtn) {
            alertBtn.addEventListener('click', () => this.show());
        }
    },
    
    show() {
        this.overlay.classList.add('show');
        this.panel.classList.add('show');
        this.loadAlerts();
    },
    
    hide() {
        this.overlay.classList.remove('show');
        this.panel.classList.remove('show');
    },
    
    async loadAlerts() {
        try {
            const response = await axios.get(`${API_BASE}/api/web/monitoring/analysis`);
            const reports = response.data.results || [];
            
            // 筛选有异常的报告
            const alerts = reports.filter(r => r.anomalies_count > 0 || r.violations_count > 0);
            
            if (alerts.length === 0) {
                this.content.innerHTML = '<div class="empty-state">暂无告警</div>';
                return;
            }
            
            this.content.innerHTML = alerts.map(alert => {
                const time = new Date(alert.timestamp).toLocaleTimeString('zh-CN', {
                    month: '2-digit',
                    day: '2-digit',
                    hour: '2-digit',
                    minute: '2-digit'
                });
                const severity = alert.violations_count > 0 ? 'danger' : 'warning';
                const colorClass = severity === 'danger' ? 'border-danger' : 'border-warning';
                
                return `
                    <div class="alert-item ${colorClass}">
                        <div class="alert-time">${time}</div>
                        <div class="alert-content">
                            <div class="alert-title">${alert.query || '异常检测'}</div>
                            <div class="alert-desc">
                                检测到 ${alert.anomalies_count} 处异常
                                ${alert.violations_count > 0 ? `，${alert.violations_count} 处违规` : ''}
                            </div>
                        </div>
                    </div>
                `;
            }).join('');
            
        } catch (error) {
            console.error('[ALERT] 加载告警失败:', error);
            this.content.innerHTML = '<div class="empty-state">加载失败</div>';
        }
    }
};

// 在 DOMContentLoaded 中初始化
document.addEventListener('DOMContentLoaded', () => {
    // ... 现有代码 ...
    
    // 初始化告警面板
    alertPanel.init();
});
```

- [ ] **Step 2: 添加告警面板样式**

在 styles.css 中添加告警面板样式：

```css
/* 告警项样式 */
.alert-item {
    border-left: 4px solid;
    padding: 12px;
    margin-bottom: 12px;
    border-radius: 4px;
    background: var(--bg-secondary);
}

.alert-item.border-danger {
    border-left-color: var(--danger);
}

.alert-item.border-warning {
    border-left-color: var(--warning);
}

.alert-time {
    font-size: 12px;
    color: var(--text-secondary);
    margin-bottom: 4px;
}

.alert-title {
    font-weight: 600;
    margin-bottom: 4px;
}

.alert-desc {
    font-size: 14px;
    color: var(--text-secondary);
}

.empty-state {
    text-align: center;
    padding: 40px 20px;
    color: var(--text-secondary);
}
```

- [ ] **Step 3: 更新告铃徽章显示**

在 loadAnalysisReports 函数中添加徽章更新逻辑（约440行）：

在函数末尾添加：
```javascript
// 更新告铃徽章
const totalAlerts = (response.data.results || []).filter(r => 
    r.anomalies_count > 0 || r.violations_count > 0
).length;

const badge = document.getElementById('alert-badge');
if (badge) {
    if (totalAlerts > 0) {
        badge.textContent = totalAlerts;
        badge.style.display = 'block';
    } else {
        badge.style.display = 'none';
    }
}
```

- [ ] **Step 4: 测试告警面板**

1. 打开 `http://localhost:8080`
2. 点击告铃图标，右侧面板应该滑出
3. 点击遮罩或关闭按钮，面板应该关闭
4. 有异常的报告时，告铃应该显示徽章数字

- [ ] **Step 5: 提交变更**

```bash
git add middleware/static/js/app.js middleware/static/css/styles.css
git commit -m "feat: add alert panel with slide-in animation"
```

---

### Task 6: 实现实时监控页指标卡片

**Files:**
- Modify: `middleware/static/js/monitoring.js`

**目标:** 在监控页面添加核心指标卡片，显示实时数据

- [ ] **Step 1: 添加指标更新逻辑**

在 updateMetricCards 函数中添加指标卡片更新（约91行）：

找到原函数并替换为：
```javascript
updateMetricCards(analysisData) {
    // 如果没有数据，显示占位符
    if (!analysisData || analysisData.length === 0) {
        document.getElementById('metric-influent-ph').textContent = '--';
        document.getElementById('metric-effluent-cod').textContent = '--';
        document.getElementById('metric-influent-tn').textContent = '--';
        document.getElementById('metric-anomalies').textContent = '--';
        return;
    }

    // 获取最新数据
    const latest = analysisData[analysisData.length - 1];
    
    // 更新指标卡片
    const updateCard = (id, value, trend = null) => {
        const el = document.getElementById(id);
        if (el && value !== undefined && value !== null) {
            el.textContent = typeof value === 'number' ? value.toFixed(1) : value;
        }
        
        // 更新趋势
        const trendEl = el.parentElement.querySelector('.metric-trend');
        if (trendEl && trend) {
            trendEl.innerHTML = trend;
        }
    };

    // 从报告中提取指标（需要分析报告包含指标数据）
    // 暂时使用默认值，后续可从 API 获取
    updateCard('metric-influent-ph', 7.2, '<span style="color: var(--success)">↑ 5%</span>');
    updateCard('metric-effluent-cod', 45, '→');
    updateCard('metric-influent-tn', 12, '<span style="color: var(--danger)">↓ 2%</span>');
    
    // 异常数从最新报告获取
    const anomalyCount = latest.anomalies_count || 0;
    const violationCount = latest.violations_count || 0;
    document.getElementById('metric-anomalies').textContent = anomalyCount;
    
    const statusEl = document.getElementById('metric-status');
    if (statusEl) {
        if (violationCount > 0) {
            statusEl.innerHTML = '<span style="color: var(--danger)">⚠️</span>';
        } else if (anomalyCount > 0) {
            statusEl.innerHTML = '<span style="color: var(--warning)">⚠️</span>';
        } else {
            statusEl.innerHTML = '<span style="color: var(--success)">✓</span>';
        }
    }
}
```

- [ ] **Step 2: 测试指标卡片**

1. 切换到实时监控页面
2. 指标卡片应该显示数值
3. 趋势箭头应该有颜色

- [ ] **Step 3: 提交变更**

```bash
git add middleware/static/js/monitoring.js
git commit -m "feat: add metric cards to monitoring page"
```

---

## 阶段3：优化和收尾（P2）

### Task 7: 清理旧的 CSS 代码

**Files:**
- Modify: `middleware/static/css/styles.css`

**目标:** 移除不再使用的旧样式，清理代码

- [ ] **Step 1: 删除旧的标签页样式**

删除以下不再使用的 CSS 类：
- `.tab-btn`
- `.header`
- `.tabs` 
- 旧的 `.panel` 样式（保留新的 `.content-panel`）

搜索并删除：
```css
/* 删除这些旧样式 */
.tab-btn { ... }
.tabs { ... }
.header .logo { ... }
.header .subtitle { ... }
```

- [ ] **Step 2: 删除旧的查询状态样式中多余的代码**

保留必要的查询状态和进度步骤样式，删除重复的。

- [ ] **Step 3: 验证功能正常**

打开 `http://localhost:8080`，测试所有功能：
1. 智能查询功能正常
2. 实时监控功能正常
3. 分析报告显示正常
4. 导航切换正常
5. 告警面板正常

- [ ] **Step 4: 提交变更**

```bash
git add middleware/static/css/styles.css
git commit -m "cleanup: remove unused CSS classes from old layout"
```

---

### Task 8: 添加过渡动画

**Files:**
- Modify: `middleware/static/css/styles.css`

**目标:** 为面板切换添加淡入动画

- [ ] **Step 1: 添加页面切换动画**

在 styles.css 中添加：

```css
/* 页面切换动画 */
.content-panel {
    animation: fade-in 300ms ease-out;
}

@keyframes fade-in {
    from {
        opacity: 0;
        transform: translateY(10px);
    }
    to {
        opacity: 1;
        transform: translateY(0);
    }
}

/* 悬浮效果 */
.metric-card:hover,
.chart-container:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    transition: all 200ms ease-out;
}

/* 按钮悬停效果 */
.btn:hover {
    transform: translateY(-1px);
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

.btn:active {
    transform: translateY(0);
}
```

- [ ] **Step 2: 测试动画效果**

1. 切换导航项，观察面板淡入动画
2. 悬浮在卡片上，观察微微上移效果
3. 点击按钮，观察下压效果

- [ ] **Step 3: 提交变更**

```bash
git add middleware/static/css/styles.css
git commit -m "style: add transition animations and hover effects"
```

---

### Task 9: 最终验证和测试

**Files:**
- All modified files

**目标:** 全面验证所有功能正常

- [ ] **Step 1: 功能测试清单**

逐项测试并记录结果：

| 测试项 | 操作 | 预期结果 | 实际结果 |
|-------|------|---------|---------|
| 智能查询 | 输入查询，点击分析 | 显示图表和结果 | |
| 实时监控 | 切换到监控页 | 显示指标和Grafana | |
| 分析报告 | 切换到报告页 | 显示报告列表 | |
| 导航切换 | 点击各导航项 | 面板切换 | |
| 侧边栏展开 | 点击展开按钮 | 导航展开 | |
| 告警面板 | 点击告铃 | 右侧面板滑出 | |
| 响应式 | 调整窗口大小 | 布局适应 | |

- [ ] **Step 2: 浏览器兼容性测试**

在不同浏览器中测试：
- Chrome/Edge: 
- Firefox:
- Safari (如有):

- [ ] **Step 3: 检查控制台错误**

打开浏览器开发者工具 Console，确保无错误。

- [ ] **Step 4: 创建最终提交**

```bash
git add -A
git commit -m "chore: final UI redesign complete - enterprise monitoring style"
```

---

## 验收标准

完成后验证：
- ✅ 左侧导航可展开/收起
- ✅ 顶部栏包含搜索、告铃、用户信息
- ✅ 配色符合企业级监控工具风格
- ✅ 告警面板可从右侧滑出
- ✅ 图表在卡片内正确渲染
- ✅ 响应式适配（>768px）
- ✅ 所有原有功能正常工作
- ✅ 无控制台错误
