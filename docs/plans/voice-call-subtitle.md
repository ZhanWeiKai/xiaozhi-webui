# 通话界面字幕显示方案

## 需求

在 VoiceCall 通话界面中实时显示字幕：
- 用户说话的文字（STT）→ 一种颜色
- AI 回答的文字（TTS/LLM）→ 另一种颜色

## 当前代码结构

```
App.vue (WebSocket 消息分发)
  ├─ case "stt"  → chatContainerRef.appendMessage(Role.USER, text)
  ├─ case "llm"  → chatContainerRef.appendMessage(Role.AI, text)
  └─ case "tts"  → chatContainerRef.appendMessage(Role.AI, text)

VoiceCall.vue (全屏通话界面)
  ├─ 头像 + 涟漪动画
  ├─ 音浪动画
  └─ 挂断按钮
  ❌ 没有字幕显示区域

ChatContainer.vue (聊天记录，VoiceCall 覆盖在它上面，看不到)
```

**问题**：VoiceCall 是全屏覆盖层，盖住了底下的 ChatContainer。通话时用户看不到任何文字。

## 实现方案

### 核心思路

在 VoiceCall.vue 内部新增一个字幕区域，直接接收字幕数据并显示。

### 涉及文件

| 文件 | 改动 |
|------|------|
| `src/components/VoiceCall.vue` | 新增字幕显示区域 + props 接收字幕数据 |
| `src/App.vue` | 将字幕数据传给 VoiceCall，同时保留 ChatContainer 记录 |

### 不需要改的文件

- `ChatContainer.vue` — 不动，继续做聊天记录
- `types/chat.ts` — 不动，Role 枚举已有 user/ai
- `types/message.ts` — 不动

### Step 1: VoiceCall.vue 新增字幕 props 和显示区域

**新增 props：**

```typescript
const props = defineProps<{
  isVisible: boolean;
  voiceAnimationManager: VoiceAnimationManager;
  chatStateManager: ChatStateManager;
  subtitleMessages: Array<{ type: 'user' | 'ai'; content: string }>;  // 新增
}>();
```

**模板新增字幕区域（放在头像和按钮之间）：**

```html
<!-- 字幕区域 -->
<div class="subtitle-container">
  <div
    v-for="(msg, index) in subtitleMessages"
    :key="index"
    :class="['subtitle-line', msg.type]"
  >
    {{ msg.content }}
  </div>
</div>
```

**样式：**

```less
.subtitle-container {
  flex: 1;
  display: flex;
  flex-direction: column;
  justify-content: flex-end;
  align-items: center;
  padding: 0 1.5rem;
  overflow-y: auto;
  scrollbar-width: none;
  max-height: 200px;
  gap: 0.5rem;

  .subtitle-line {
    max-width: 85%;
    padding: 0.4rem 0.8rem;
    border-radius: 0.5rem;
    font-size: 0.95rem;
    line-height: 1.5;
    word-break: break-word;
    animation: fadeIn 0.3s ease-in;

    &.user {
      background: rgba(59, 130, 246, 0.2);    /* 蓝色半透明背景 */
      color: #93c5fd;                          /* 浅蓝文字 */
      align-self: flex-end;
      border-radius: 0.8rem 0.8rem 0.2rem 0.8rem;
    }

    &.ai {
      background: rgba(34, 197, 94, 0.2);     /* 绿色半透明背景 */
      color: #86efac;                          /* 浅绿文字 */
      align-self: flex-start;
      border-radius: 0.8rem 0.8rem 0.8rem 0.2rem;
    }
  }
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}
```

### Step 2: App.vue 维护字幕列表并传递给 VoiceCall

在 App.vue 中新增一个响应式数组，只在最近 N 条消息中保留：

```typescript
import { ref } from "vue";

// 通话界面字幕（只保留最近 10 条）
const subtitleMessages = ref<Array<{ type: 'user' | 'ai'; content: string }>>([]);

const MAX_SUBTITLE_COUNT = 10;

const addSubtitle = (type: 'user' | 'ai', text: string) => {
  subtitleMessages.value.push({ type, content: text });
  if (subtitleMessages.value.length > MAX_SUBTITLE_COUNT) {
    subtitleMessages.value.shift();
  }
};
```

在现有的 `onTextMessage` 回调中，追加字幕：

```typescript
case "stt":
  const sttMessage = message as UserEcho;
  if (sttMessage.text?.trim()) {
    chatContainerRef.value?.appendMessage(Role.USER, sttMessage.text);
    addSubtitle('user', sttMessage.text);  // 新增
  }
  break;

case "llm":
  const emotionMessage = message as AIResponse_Emotion;
  if (emotionMessage.text?.trim()) {
    chatContainerRef.value?.appendMessage(Role.AI, emotionMessage.text);
    addSubtitle('ai', emotionMessage.text);  // 新增
  }
  break;

case "tts":
  if (message.state === "sentence_start") {
    const textMessage = message as AIResponse_Text;
    // ... 原有 blacklist 逻辑 ...
    chatContainerRef.value?.appendMessage(Role.AI, textMessage.text!);
    addSubtitle('ai', textMessage.text!);  // 新增
  }
  break;
```

关闭通话面板时清空字幕：

```typescript
const closeVoiceCallPanel = async () => {
  isVoiceCallVisible.value = false;
  subtitleMessages.value = [];  // 清空字幕
  sendAbortMessage();
  audioService.stopMediaResources();
};
```

模板中传递 props：

```html
<VoiceCall
  :voice-animation-manager="voiceAnimationManager"
  :chat-state-manager="chatStateManager"
  :is-visible="isVoiceCallVisible"
  :subtitle-messages="subtitleMessages"          <!-- 新增 -->
  @on-shut-down="closeVoiceCallPanel"
/>
```

## 界面布局（改后）

```
┌──────────────────────────┐
│                          │
│      ┌──────────┐        │
│      │  头像     │        │  上方：头像 + 涟漪
│      └──────────┘        │
│                          │
│   ~~~~ 音浪动画 ~~~~     │  中间：音浪
│                          │
│  ┌─────────────────────┐ │
│  │ AI: 你好，今天天气  │ │  ← 绿色
│  │       USER: 外面下  │ │  ← 蓝色 (右对齐)
│  │ AI: 是的，我记得明 │ │  ← 绿色
│  └─────────────────────┘ │  下方：字幕区域
│                          │
│        📞 挂断           │  底部：挂断按钮
└──────────────────────────┘
```

## 颜色方案

| 角色 | 背景色 | 文字色 | 对齐 |
|------|--------|--------|------|
| 用户 (user) | 蓝色半透明 `rgba(59,130,246,0.2)` | 浅蓝 `#93c5fd` | 右对齐 |
| AI (ai) | 绿色半透明 `rgba(34,197,94,0.2)` | 浅绿 `#86efac` | 左对齐 |

暗色背景 (#151414) 上，蓝色和绿色对比度好，容易区分。

## 总结

改动量很小：
1. **VoiceCall.vue** — 加 props + 字幕区域 HTML + CSS（~40 行）
2. **App.vue** — 加 `subtitleMessages` 数组 + `addSubtitle` 调用 + props 传递（~15 行）
3. 其他文件不动
