<script setup lang="ts">
import { ref, onMounted, onUnmounted } from "vue";
import { useSettingStore } from "./stores/setting";
import type {
  HelloResponse,
  UserEcho,
  AIResponse_Emotion,
  AIResponse_Text,
  AbortMessage,
  UserMessage
} from "./types/message";

const settingStore = useSettingStore();

// ---------- 语音对话配置 start --------------
import { ChatStateManager } from "./services/ChatStateManager";
import { ChatEvent, ChatState } from "./types/chat";
import { VoiceAnimationManager } from "./services/VoiceAnimationManager";
import { AudioService } from "./services/AudioManager";

const voiceAnimationManager = new VoiceAnimationManager();
const chatStateManager = new ChatStateManager({
  thresholds: {
    USER_SPEAKING: 0.04,
    USER_INTERRUPT_AI: 0.1,
  },
  timeout: {
    SILENCE: 1000
  },
  callbacks: {
    sendAudioData(data: Float32Array) {
      wsService.sendAudioMessage(data);
    },
    sendTextData(text: string) {
      wsService.sendTextMessage(text);
    },
    getSessionId() {
      return settingStore.sessionId;
    }
  },
  voiceAnimationManager: voiceAnimationManager,
})
const audioService = AudioService.getInstance();
audioService.onQueueEmpty(() => {
  chatStateManager.setState(ChatState.IDLE);
})
audioService.onProcess((audioLevel: number, audioData: Float32Array) => {
  chatStateManager.handleUserAudioLevel(audioLevel, audioData);
})
chatStateManager.on(ChatEvent.USER_START_SPEAKING, async () => {
  audioService.stopPlaying();
  audioService.clearAudioQueue();
})
chatStateManager.on(ChatEvent.AI_START_SPEAKING, () => {
  audioService.playAudio();
})
// ---------- 语音对话配置 end ----------------

// ---------- WebSocket 配置 start ----------
import { WebSocketService } from "./services/WebSocketManager";
const wsService = new WebSocketService({
  decodeAudioData: (arrayBuffer: ArrayBuffer) => audioService.decodeAudioData(arrayBuffer),
  settingStore: settingStore,
},{
  async onAudioMessage(audioBuffer) {
    console.log("[WebSocketService][onAudioMessage] audio data received.");
    switch (chatStateManager.currentState.value as ChatState) {
      case ChatState.USER_SPEAKING:
        console.warn("[WebSocketService][onAudioMessage] User is speaking, discarding audio data.");
        audioService.enqueueAudio(audioBuffer);
        break;
      case ChatState.IDLE:
        console.log("[WebSocketService][onAudioMessage] Audio is not playing, set ai speaking...");
        audioService.enqueueAudio(audioBuffer);
        chatStateManager.setState(ChatState.AI_SPEAKING);
        break;
      case ChatState.AI_SPEAKING:
        console.log("[WebSocketService][onAudioMessage] AI is speaking, enqueuing audio data.");
        audioService.enqueueAudio(audioBuffer);
        break;
      default:
        console.error("[WebSocketService][onAudioMessage] Unknown state:", chatStateManager.currentState.value);
    }
  },
  async onTextMessage(message) {
    console.log("[WebSocketService][onTextmessage] Text message received:", message);
    switch (message.type) {
      case "hello":
        const helloMessage = message as HelloResponse;
        settingStore.sessionId = helloMessage.session_id!;
        console.log("[WebSocketService][onTextmessage] Session ID:", helloMessage.session_id);
        break;
    }
  },
  onConnect() {
    console.log("连接成功");
  },
  onDisconnect() {
    console.log("连接已断开，正在尝试重连");
    setTimeout(() => {
      wsService.connect(settingStore.wsProxyUrl);
    }, 3000);
  }
})
// ---------- WebSocket 配置 end ------------

import ConnectionStatus from './components/Header/ConnectionStatus.vue'
import SettingPanel from './components/Setting/index.vue'
import VoiceCall from "./components/VoiceCall.vue";
import { ElMessage, ElMessageBox } from 'element-plus';

const sendAbortMessage = () => {
  const abortMessage: AbortMessage = {
    type: "abort",
    session_id: settingStore.sessionId,
  };
  wsService.sendTextMessage(abortMessage)
}

const isVoiceCallVisible = ref<boolean>(false);

const showVoiceCallPanel = async () => {
  sendAbortMessage();
  audioService.clearAudioQueue();
  isVoiceCallVisible.value = true;
  await audioService.prepareMediaResources();
  if (chatStateManager.currentState.value != ChatState.IDLE) {
    chatStateManager.setState(ChatState.IDLE);
  }
};

const closeVoiceCallPanel = async () => {
  isVoiceCallVisible.value = false;
  sendAbortMessage();
  audioService.stopMediaResources();
};

const ensureBackendUrl = async () => {
  if (!settingStore.backendUrl) {
    const { value: backendUrl } = await ElMessageBox.prompt('请输入本地服务器地址：', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      inputValue: 'http://localhost:8081',
      inputPattern: /^http(s?):\/\/.+/,
      inputErrorMessage: '请输入有效的服务器地址(http:// 或 https:// 开头)',
    });
    settingStore.backendUrl = backendUrl;
    ElMessage.success("后端服务器地址已保存");
  }
}

onMounted(async () => {
  // Always use hardcoded HTTPS config for production
  // Clear old localStorage cache if it contains insecure URLs
  const localConfig = localStorage.getItem('settings')
  if (localConfig && localConfig.includes('ws://')) {
    console.log("[App][onMounted] 清除旧的 HTTP 配置缓存")
    localStorage.removeItem('settings')
  }

  // Load from localStorage (will be empty if we just cleared it)
  settingStore.loadFromLocal();

  // Always use hardcoded default config (HTTPS)
  wsService.connect(settingStore.wsProxyUrl);

  // Optionally try to fetch latest config from backend
  try {
    const fetchOk = await settingStore.fetchConfig();
    if (fetchOk) {
      settingStore.saveToLocal();
      console.log("[App][onMounted] 配置已从后端更新");
    }
  } catch (e) {
    console.warn("[App][onMounted] 无法从后端获取配置，使用默认配置", e);
  }
});

onUnmounted(() => {
  console.log("[App][onUnmounted] Clearing resources...");
  chatStateManager.destroy();
  audioService.clearMediaResources();
});
</script>

<template>
  <div class="app-container">
    <!-- 左上角状态 -->
    <ConnectionStatus :connection-status="wsService.connectionStatus.value" />

    <!-- 中央通话按钮 -->
    <div class="call-button-container">
      <button class="call-button" @click="showVoiceCallPanel">
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor">
          <path d="M2 3a1 1 0 011-1h2.153a1 1 0 01.986.836l.74 4.435a1 1 0 01-.54 1.06l-1.548.773a11.037 11.037 0 006.105 6.105l.774-1.548a1 1 0 011.059-.54l4.435.74a1 1 0 01.836.986V17a1 1 0 01-1 1h-2C7.82 18 2 12.18 2 5V3z" />
        </svg>
      </button>
    </div>

    <!-- 设置面板 -->
    <SettingPanel />

    <!-- 语音通话面板 -->
    <VoiceCall
      :voice-animation-manager="voiceAnimationManager"
      :chat-state-manager="chatStateManager"
      :is-visible="isVoiceCallVisible"
      @on-shut-down="closeVoiceCallPanel"
    />
  </div>
</template>

<style>
/* 全局重置 */
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

html, body {
  height: 100%;
  background-color: #FFFFFF;
}

#app {
  height: 100%;
  background-color: #FFFFFF;
}

.app-container {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100vh;
  background-color: #FFFFFF;
  overflow: hidden;
}

.call-button-container {
  display: flex;
  align-items: center;
  justify-content: center;
}

.call-button {
  width: 80px;
  height: 80px;
  border-radius: 50%;
  border: none;
  background-color: #10b981;
  color: white;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s ease;
  box-shadow: 0 4px 12px rgba(16, 185, 129, 0.3);
}

.call-button:hover {
  transform: scale(1.05);
  box-shadow: 0 6px 16px rgba(16, 185, 129, 0.4);
}

.call-button:active {
  transform: scale(0.95);
}

.call-button svg {
  width: 36px;
  height: 36px;
}
</style>
