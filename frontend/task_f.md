# task_f — 前端开发任务指南

> 本文档是前端开发的具体步骤拆解。每一步完成后在 `help.md` 的任务表中标记 ✅。
> 设计参考：**Notion / Vercel** — 极简科技感、温和色调、留白充分。
> 适配策略：**移动端优先**，先写手机端样式，再通过媒体查询扩展至桌面。
> 标记说明：**🆕 = 本次新增/修改**

---

## 页面清单（共 4 页）

| 页面 | 文件 | 路由 |
|------|------|------|
| 首页（排行榜） | `index.html` | `/` |
| 播放页 | `play.html` | `/play.html?id={audio_id}` |
| 上传页 | `upload.html` | `/upload.html` |
| 后台管理 | `admin.html` | `/admin.html` |

> Nginx 可配置 `try_files` 实现无 `.html` 后缀访问；为简单起见，开发阶段链接直接用 `.html` 路径。

---

## 通用准备

### 0.1 CSS 设计 Token（写在 `css/style.css` 顶部）

按 Notion / Vercel 的调性设定以下变量：

```
:root {
  --bg:         #ffffff;
  --bg-soft:    #f7f7f5;      /* 浅灰底，类似 Notion 侧边栏 */
  --text:       #1a1a1a;
  --text-muted: #6b6b6b;
  --border:     #e6e6e4;
  --accent:     #1a1a1a;      /* 主色调：黑/深灰，不用高饱和色 */
  --accent-soft:#f0f0ed;
  --radius:     8px;
  --font:       "Inter", "SF Pro Text", -apple-system, sans-serif;
  --max-w:      640px;        /* 单栏最大宽度，Notion 风格 */
}
```

### 0.2 引入外部依赖（`<head>` 中）

```html
<link rel="stylesheet" href="/css/style.css">
<script defer src="https://cdn.jsdelivr.net/npm/alpinejs@3.x.x/dist/cdn.min.js"></script>
```

> 不再引入其他 CSS 框架，手写 CSS 以保持对设计的完全控制。

### 0.3 通用布局结构

每页都遵循相同的壳：

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>最会打呼之人</title>
  <link rel="stylesheet" href="/css/style.css">
  <script defer src="https://cdn.jsdelivr.net/npm/alpinejs@3.x.x/dist/cdn.min.js"></script>
</head>
<body>
  <header class="site-header"><!-- 导航栏 --></header>
  <main class="site-main"><!-- 页面内容 --></main>
  <footer class="site-footer"><!-- 版权/链接 --></footer>
</body>
</html>
```

### 0.4 公共 JS 工具（`js/utils.js`）

```js
// API 基础路径（部署时替换）
const API_BASE = '/api';

// 通用 GET 请求
async function apiGet(path) {
  const res = await fetch(API_BASE + path);
  if (!res.ok) throw new Error(res.statusText);
  return res.json();
}

// 通用 POST 请求
async function apiPost(path, body) {
  const res = await fetch(API_BASE + path, {
    method: 'POST',
    headers: body instanceof FormData ? {} : { 'Content-Type': 'application/json' },
    body: body instanceof FormData ? body : JSON.stringify(body),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || res.statusText);
  }
  return res.json();
}

// 复制文本到剪贴板
async function copyToClipboard(text) {
  await navigator.clipboard.writeText(text);
}

// 格式化日期为相对时间
function formatTime(isoString) {
  const d = new Date(isoString);
  const now = new Date();
  const diff = now - d;
  if (diff < 3600000) return Math.floor(diff / 60000) + '分钟前';
  if (diff < 86400000) return Math.floor(diff / 3600000) + '小时前';
  if (diff < 604800000) return Math.floor(diff / 86400000) + '天前';
  return d.toLocaleDateString('zh-CN');
}
```

---

## 一、首页 `index.html`

### 步骤 1.1：页面结构

- 顶部导航栏：网站名称"最会打呼之人" + 右侧"上传我的呼噜"按钮
- Tab 栏：点赞榜 | 评分榜
- 时间筛选：全部 | 本周 | 今日
- 排行榜列表：每条显示排名、昵称、时长、点赞数/评分、播放按钮

### 步骤 1.2：Alpine.js 数据流

```js
x-data="{
  tab: 'likes',       // 'likes' | 'scores'
  range: 'all',       // 'all' | 'week' | 'today'
  items: [],
  loading: false,
  async fetchLeaderboard() { ... },
  init() { this.fetchLeaderboard(); }
}"
```

### 步骤 1.3：API 调用

- `GET /api/leaderboard/likes?range=all|week|today` → 点赞榜
- `GET /api/leaderboard/scores?range=all|week|today` → 评分榜

### 步骤 1.4：UI 细节

- 每条目：左侧排名数字（Top 3 用金色/银色/铜色），右侧播放图标箭头
- 点击条目跳转 `/play?id={audio_id}`
- 列表底部署"加载更多"（或直接显示 Top 10）
- 空状态：榜单为空时显示"还没有人上传呼噜，来做第一个吧！"

### 步骤 1.5：移动端适配

- 单栏布局，列表撑满宽度，边距 16px
- Tab 栏横向排列，字体不缩放
- 🆕 **浮动上传按钮（FAB）**：固定在页面右下角，圆形"＋"按钮，点击跳转上传页
  - CSS：`position: fixed; bottom: 24px; right: 24px; z-index: 100;`
  - 仅在移动端显示（≤640px），桌面端使用顶部导航栏中的上传按钮

---

## 二、播放页 `play.html`

### 步骤 2.1：页面结构

- 返回按钮（左上角 ← 箭头）
- 音频标题区（昵称 + 上传时间）
- `<audio>` 播放器（浏览器原生控件）
- 🆕 **AI 智能诊断区**（醒目位置，大号引文风格的一句话诊断）
- 算法评分展示区（分数 + 五维度详情可折叠）
- 🆕 AI 四维度条（节奏/能量/爆发力/感染力，带进度条和短评）
- 操作按钮行：点赞 👍 | 点踩 👎 | 分享 📋
- 点赞/点踩数显示

### 步骤 2.2：获取音频详情

URL 参数 `?id=` 获取 `audio_id`，调用：
- `GET /api/audio/{id}` → 返回全部字段

### 步骤 2.3：操作交互

- **点赞**：`POST /api/audio/{id}/like` → 成功后按钮变色并 +1
- **点踩**：`POST /api/audio/{id}/dislike` → 同上
- **分享**：`navigator.clipboard.writeText(window.location.href)` → 显示 Toast "链接已复制！"
- 点赞/点踩状态存入 `localStorage`，刷新后仍显示（已点赞/已点踩）

### 步骤 2.4：评分展示

分为两个区域：

**A. 算法评分（Librosa 五维度）**：
- 大号分数（如 87.3）——标注"算法综合评分"
- 可折叠的五维度详情表（响度峰值、频率特色、持续稳定性、动态范围、时长）

**B. 🆕 AI 智能诊断（DeepSeek 四维度）**：
- **诊断卡片**：浅色背景卡片，左侧 AI 图标，右侧大号引用风格的一句话诊断文字（`audio.ai_commentary`）
  - 示例：*"有种重型机械缓慢驶过月球表面的震撼。"*
- **四维度条**：使用 `ai_dimensions` 中的 rhythm / energy / burst / impact
  - 每个维度一行：名称（节奏/能量/爆发力/感染力）+ 分数条（彩色进度条）+ 短评
- AI 诊断区与算法评分区之间用分隔线或明显标题区分：**"🤖 AI 智能诊断"**
- 若 `ai_commentary` 为 null（AI 尚未完成或失败），显示"AI 诊断生成中…"的温和加载态

### 步骤 2.5：错误处理

- 音频不存在 → "这个呼噜不见了 😴"
- 加载中 → 骨架屏（灰色占位块）

---

## 三、上传页 `upload.html`

### 步骤 3.1：页面结构

- 拖拽区 / 点击选择文件（虚线框 + 图标）
- 文件信息预览（文件名、时长、大小）
- 昵称输入框（placeholder: "留空则自动生成匿名代号"）
- 提交按钮
- 上传进度条

### 步骤 3.2：文件校验（前端）

- 格式：仅 `.mp3` `.wav` `.ogg` `.webm`
- 大小：≤ 10MB
- 时长：使用 `<audio>` 元素预加载获取 duration，≤ 180 秒（3 分钟）
- 校验失败 → 红色提示句，不发起上传

### 步骤 3.3：上传流程

> ⚠️ 上传使用原生 `XMLHttpRequest`（需要 `upload.onprogress` 回调获取进度），**不能**复用 `utils.js` 中的 `apiPost`（它基于 fetch，不支持上传进度）。

```
表单提交 → 创建 XHR → POST /api/audio/upload (FormData: file + nickname)
  → xhr.upload.onprogress → 更新进度条百分比
  → 成功后跳转 /play.html?id={返回的 audio_id}
  → 失败后显示错误信息
```

### 步骤 3.4：上传状态管理

```js
x-data="{
  file: null,
  nickname: '',
  uploading: false,
  progress: 0,
  error: '',
  validate() { ... },
  async submit() { ... },
}"
```

---

## 四、后台管理 `admin.html`

### 步骤 4.1：鉴权流程

- 页面加载时弹出 prompt 输入管理密码
- 密码存入 JS 变量（仅在当前会话保留），每次 API 请求通过 `Authorization: Bearer <密码>` 头传递
- 后端验证失败 → 返回 401 → 前端显示"无权限"并跳回首页
- 鉴权完全由后端负责，前端的密码输入只是获取 token 的入口

### 步骤 4.2：页面结构

- 统计概览卡片行：总音频数、总点赞数、今日新增
- 音频列表表格：ID、昵称、上传时间、评分、操作（删除按钮）
- 删除按钮 → 确认弹窗 → 调用删除 API（带 `Authorization` 头）

### 步骤 4.3：API 调用

所有管理 API 请求需附带 `Authorization: Bearer <token>` 请求头：

- `GET /api/admin/stats` → 统计数据
- `GET /api/admin/audios?page=1&size=20` → 音频列表（分页）
- `DELETE /api/admin/audios/{id}` → 删除音频

---

## 五、补充样式指南

### 🆕 5.1 AI 诊断区样式指南

| 元素 | 样式规范 |
|------|---------|
| AI 诊断卡片 | `background: var(--bg-soft); border-radius: var(--radius); padding: 20px;` |
| 一句话诊断 | `font-size: 1.1rem; font-weight: 600; line-height: 1.7;` 左侧加 AI 图标 🤖 |
| 维度行 | `display: flex; align-items: center; gap: 12px; margin-top: 12px;` |
| 维度标签 | `font-size: 0.8rem; color: var(--text-muted); width: 60px;` |
| 进度条 | `height: 6px; border-radius: 3px; background: var(--border);` 填充色用 `var(--accent)` |
| 短评 | `font-size: 0.75rem; color: var(--text-muted); width: 120px; text-align: right;` |

### 5.2 动画

- 点赞/点踩：按钮放大 → 缩回（`transform: scale(1.2)` 持续 150ms）
- Toast：从底部滑入 → 2 秒后滑出
- 页面切换：无动画（SPA 暂不做路由过渡）

### 5.2 断点

| 断点 | 目标 |
|------|------|
| 0–640px | 手机（优先） |
| 641–1024px | 平板 |
| 1025px+ | 桌面——内容居中，最大宽度 640px |

### 5.3 可访问性

- 按钮必须有 `aria-label`
- `<audio>` 控件自带键盘可访问
- 颜色对比度满足 WCAG AA

---

## 六、首页三段式分离 + 渐变过渡

> 背景：snore-social 模板将 Hero / 排行榜 / 怎么玩 合成在 index.html 一个长页面中。
> 需求：视觉上拆分为三个独立"页"，通过导航点击平滑跳转，加入渐变过渡效果。

### 步骤 6.1：导航栏增强

- 导航链接点击 → 平滑滚动到对应 section（`scroll-behavior: smooth` + JS `scrollIntoView`）
- 滚动监听（Intersection Observer）→ 当前所在 section 对应的导航项高亮（文字变橙、底部加下划线）
- 移动端导航保持简洁

### 步骤 6.2：Section 视觉分离

- 每个 section 之间加 **渐变过渡条**（`h-8 bg-gradient-to-b from-[#fffaf5] to-white`）
- 排行榜 section 背景为 `white`，Hero 和 怎么玩 背景为 `#fffaf5`，形成色块区隔
- 每个 section 进入视口时触发 **淡入动画**（opacity 0→1 + translateY 20px→0）

### 步骤 6.3：Hero 区域优化

- 首屏高度至少 `min-h-[85vh]`，确保打开页面时看不到下方内容
- 底部加入**向下滚动提示**（脉动箭头图标 + "往下看" 文字）
- 点击箭头 → 平滑滚动到排行榜

### 步骤 6.4：怎么玩页面独立感

- 改为全宽暖橙底（`bg-[#fff0df]`），与上方排行榜 white 底形成强对比
- 加入顶部渐变过渡（white → `#fff0df`）
- 三步卡片加 hover 上浮效果

### 步骤 6.5：滚动动画系统

- 使用 Intersection Observer 监听每个 section
- 进入视口 30% 时触发：
  - section 内容：`opacity: 0 → 1`，`translateY(30px → 0)`
  - 过渡时长：600ms，ease-out
- 已经在视口内的不再重复触发（once: true）

### 步骤 6.6：移动端适配

- 首屏高度 `min-h-[90vh]`
- 渐变过渡条在移动端缩窄（h-4）
- 滚动提示箭头在移动端位置调整

---

*关联文档：Vision.md（总体设计）· help.md（需求 & 进度追踪）*
