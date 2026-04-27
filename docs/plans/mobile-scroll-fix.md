# 移动端聊天窗口滚动穿透修复方案

## 问题描述

在手机上访问 WebUI，手指在聊天窗口内上下滑动时，不会滚动聊天内容，而是带动整个 webview 滚动。

## 原因分析

手机触摸事件的默认行为：touch 事件会冒泡到 body，触发整个页面的滚动。即使 `.app-container` 设了 `overflow: hidden`，手机浏览器不完全遵守 CSS overflow 约束。

### 当前布局

```
.app-container (height: 100vh, overflow: hidden)
├── Header (蓝色顶部)
├── .chat-container (flex: 1, overflow-y: auto)  ← 问题区域
│   └── 聊天消息列表
└── InputField (输入框 + 按钮)
```

## 修改方案

### 修改文件

| 文件 | 改动类型 | 说明 |
|------|---------|------|
| `src/components/ChatContainer.vue` | **修改** | CSS 新增 `touch-action` 属性 |

### 不需要改的文件

- `App.vue` — 不动
- `InputField.vue` — 不动
- `VoiceCall.vue` — 不动

### 具体改动

**文件：`src/components/ChatContainer.vue`**

在 `.chat-container` 的 CSS 中新增一行：

```less
.chat-container {
  flex: 1;
  margin: 0.5rem;
  padding: 0.5rem;
  background-color: #f9fafb;
  border: 1px solid #e5e7eb;
  border-radius: 0.5rem;
  overflow-y: auto;
  scrollbar-width: none;
  touch-action: pan-y;      /* ← 新增：允许垂直平移，禁止浏览器默认触摸行为 */
```

## 原理

`touch-action: pan-y` 告诉浏览器：
- 这个元素内部的垂直滚动由元素自己处理（`overflow-y: auto`）
- 不要把 touch 事件冒泡给 body
- 不影响水平滚动和其他触摸手势

## 影响范围

- 只影响 `.chat-container` 元素的触摸行为
- 不影响 Header 区域的触摸（Header 没有 `touch-action`，保持默认行为）
- 不影响 InputField 的输入操作
- 桌面端完全不受影响（`touch-action` 只对触摸屏生效）
- 不影响其他组件的任何功能
