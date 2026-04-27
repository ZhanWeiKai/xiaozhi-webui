<script setup lang="ts">
import { ref, nextTick } from "vue";
import type { Message } from "@/types/message";
import type { Role } from "@/types/chat";

const props = defineProps<{
  disabled?: boolean;
}>();

const emit = defineEmits<{
  (e: "playTts", text: string): void;
}>();

const messages = ref<Message[]>([]);

// 处理文本内容，去除结尾的，。标点符号
const processText = (text: string): string => {
  text = text.replace(/[，。]$/, "");
  return text;
};

const appendMessage = (type: Role, text: string) => {
  const now = new Date();
  messages.value.push({
    type,
    content: processText(text),
    time: now.toLocaleTimeString("zh-CN", {
      hour: "2-digit",
      minute: "2-digit",
    }),
  });
  nextTick(() => {
    const container = document.querySelector(".chat-container");
    if (container) {
      container.scrollTop = container.scrollHeight;
    }
  });
};

const playMessage = (text: string) => {
  if (props.disabled) return;
  emit("playTts", text);
};

defineExpose({
  appendMessage,
  messages,
});
</script>

<template>
  <div class="chat-container" ref="chatContainerRef">
    <div
      v-for="(msg, index) in messages"
      :key="index"
      :class="['message', msg.type]"
    >
      <div class="message-content" v-html="msg.content"></div>
      <div class="message-time">{{ msg.time }}</div>
      <button
        v-if="msg.type === 'ai'"
        class="play-tts-btn"
        :disabled="disabled"
        @click="playMessage(msg.content)"
      >
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor">
          <path d="M3 9v6h4l5 5V4L7 9H3zm13.5 3c0-1.77-1.02-3.29-2.5-4.03v8.05c1.48-.73 2.5-2.25 2.5-4.02z"/>
        </svg>
      </button>
    </div>
  </div>
</template>

<style scoped lang="less">
.chat-container {
  flex: 1;
  margin: 0.5rem;
  padding: 0.5rem;
  background-color: #f9fafb;
  border: 1px solid #e5e7eb;
  border-radius: 0.5rem;
  overflow-y: auto;
  scrollbar-width: none;
  touch-action: pan-y;

  .message.ai,
  .message.user {
    .message-content {
      width: max-content;
      padding: 0.5rem 1rem;
      white-space: pre-line;
      text-overflow: ellipsis;
      cursor: text;
      overflow-wrap: break-word;
      word-break: break-word;
      max-width: 89%;
    }

    .message-time {
      color: #9ca3af;
      font-size: 0.75rem;
      margin-top: 0.25rem;
    }
  }

  .message.ai {
    margin: 0.5rem 0;

    .message-content {
      background-color: #fff;
      border: 1px solid #e5e7eb;
      box-shadow: 1px 1px 2px rgba(0, 0, 0, 0.1);
      border-radius: 1rem 1rem 1rem 5px;
      color: #232b36;
    }

    .play-tts-btn {
      margin-top: 0.15rem;
      width: 1.5rem;
      height: 1.5rem;
      padding: 0.15rem;
      background-color: #f59e0b;
      border: none;
      border-radius: 50%;
      color: white;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      opacity: 0.6;
      transition: opacity 0.2s;

      &:hover {
        opacity: 1;
      }

      &:disabled {
        opacity: 0.3;
        cursor: not-allowed;
      }

      svg {
        width: 0.8rem;
        height: 0.8rem;
      }
    }
  }

  .message.user {
    margin: 0.5rem 0;

    .message-content {
      background-color: var(--primary-color);
      border-radius: 1rem 1rem 5px 1rem;
      color: white;
      margin-left: auto;
    }

    .message-time {
      text-align: right;
    }
  }
}
</style>
