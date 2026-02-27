<script lang="ts" setup>
import { computed } from 'vue';

const connectionStatusClass = computed(() => props.connectionStatus);
const connectionStatusText = computed(() => {
    const texts = {
        connected: '在线',
        disconnected: '离线',
        error: '错误'
    }
    return texts[props.connectionStatus];
});

const props = defineProps<{
    connectionStatus: 'connected' | 'disconnected' | 'error'
}>()
</script>

<template>
    <div class="status-container">
        <div :class="['connection-status', connectionStatusClass]">
            {{ connectionStatusText }}
        </div>
    </div>
</template>

<style scoped lang="less">
.status-container {
    position: fixed;
    top: 0;
    left: 0;
    padding: 1rem;
    z-index: 100;

    .connection-status {
        display: flex;
        align-items: center;
        padding: 6px 12px;
        border-radius: 1rem;
        font-size: 0.9rem;

        &.connected {
            color: #10b981;
            background-color: rgba(16, 185, 129, 0.1);

            &::before {
                content: "";
                width: 8px;
                height: 8px;
                border-radius: 50%;
                background-color: #10b981;
                margin-right: 8px;
            }
        }

        &.disconnected {
            color: #9ca3af;
            background-color: rgba(156, 163, 175, 0.1);

            &::before {
                content: "";
                width: 8px;
                height: 8px;
                border-radius: 50%;
                background-color: #9ca3af;
                margin-right: 8px;
            }
        }

        &.error {
            color: #ef4444;
            background-color: rgba(239, 68, 68, 0.1);

            &::before {
                content: "";
                width: 8px;
                height: 8px;
                border-radius: 50%;
                background-color: #ef4444;
                margin-right: 8px;
            }
        }
    }
}
</style>
