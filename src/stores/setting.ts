import { ref, type Ref } from 'vue'
import { defineStore } from 'pinia'
import { log, warn } from '@/common/log'

export const useSettingStore = defineStore('setting', () => {
	// state
	const sessionId = ref<string>("")
	const wsProxyUrl = ref<string>("")
	const visible = ref<boolean>(false)

	const configRefMap: Record<string, Ref<string>> = {
		ws_proxy_url: wsProxyUrl,
	}

	const saveToLocal = (): boolean => {
		const configJson = {
			ws_proxy_url: wsProxyUrl.value,
		}

		const dataOK = Object.values(configJson).every((value) => value !== "")

		if (dataOK) {
			localStorage.setItem('settings', JSON.stringify(configJson))
			log("配置文件更新成功", configJson)
		} else {
			warn("配置文件数据不完整，未保存", configJson)
		}
		return dataOK
	}

	const updateConfig = (settings: any) => {
		Object.entries(configRefMap).forEach(([key, ref]) => {
			if (settings[key] !== undefined && settings[key] !== null) {
				ref.value = settings[key]
			}
		})
	}

	const loadFromLocal = (): boolean => {
		const localConfig = localStorage.getItem('settings')
		if (localConfig) {
			updateConfig(JSON.parse(localConfig))
			log("配置文件加载成功")
			return true
		}
		log("配置文件不存在")
		return false
	}

	const destoryLocal = () => {
		localStorage.removeItem('settings')
		log("本地缓存配置文件已删除")
	}

	return {
		sessionId,
		wsProxyUrl,
		visible,
		updateConfig,
		saveToLocal,
		loadFromLocal,
		destoryLocal,
	}
})

