<script lang="ts" setup>
import { useSettingStore } from "../../stores/setting";
import { ElMessage } from "element-plus";

const settingStore = useSettingStore();

const handleQuit = () => {
  const saveOK = settingStore.saveToLocal();
  if (!saveOK) {
    ElMessage.error("配置保存失败，请确认数据不为空");
    return;
  }
  settingStore.visible = false;
  ElMessage.success("配置已保存");
};
</script>

<template>
  <div class="setting-panel" :class="{ visible: settingStore.visible }">
    <div class="setting-content">
      <h2>设置</h2>
      <div style="display: flex; flex-direction: column">
        <label>本地代理地址</label>
        <input
          v-model="settingStore.wsProxyUrl"
          type="text"
          placeholder="例如: ws://localhost:5000"
        />
      </div>
    </div>
    <div class="bottom-buttons">
      <button id="quit" @click="handleQuit">退出</button>
    </div>
  </div>
</template>

<style lang="less" scoped>
input {
  padding: 0.6rem 0.8rem;
  outline: none;
  border: none;
  border: 1px solid #e5e7eb;
  border-radius: 0.5rem;
  transition: all 0.1s ease-in-out;

  &:focus {
    border-color: var(--primary-color);
    box-shadow: var(--primary-neo-color) 0 0 0 2px;
  }
}

.setting-panel {
  position: absolute;
  display: flex;
  padding: 1rem;
  width: 100%;
  height: 100%;
  transition: all 0.1s ease-in-out;
  background-color: #fff;
  transform: translateX(100%);
  overflow: hidden;

  &.visible {
    transform: translateX(0);
  }

  .setting-content {
    flex: 1;
    padding: 1rem;

    h2 {
      margin-bottom: 1rem;
      font-size: 1.5rem;
      font-weight: bold;
    }

    label {
      margin-bottom: 0.5rem;
      font-size: 0.9rem;
    }

    input {
      margin-bottom: 1rem;
      line-height: 1.5rem;
    }
  }

  .bottom-buttons {
    display: flex;
    justify-content: space-evenly;
    align-items: center;
    width: 100%;
    padding: 1rem 0;
    position: absolute;
    bottom: 0;
    left: 0;
    border-top: 1px solid #e5e7eb;

    #quit {
      width: 45%;
      padding: 0.8rem 0.8rem;
      color: #fff;
      font-size: 1rem;
      border: none;
      border-radius: 0.5rem;
      background-color: #f43f5e;
    }
  }
}
</style>
