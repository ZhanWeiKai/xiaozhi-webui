import { ref, type Ref } from 'vue'
import { defineStore } from 'pinia'

type ConfigData = {
	[key: string]: string | boolean,
	ws_url: string
	ws_proxy_url: string
	ota_version_url: string,
	backend_url: string,
	token_enable: boolean
	token: string
	device_id: string
}

// Hardcoded default config for production deployment (HTTPS)
const DEFAULT_CONFIG = {
	ws_url: "wss://xiaozhi-ws.jamesweb.org",
	ws_proxy_url: "wss://xiaozhi-ws.jamesweb.org",
	ota_version_url: "https://xiaozhi.jamesweb.org/api/ota",
	backend_url: "https://xiaozhi.jamesweb.org/api",
	token_enable: true,
	token: "N9tieuHFjJ_u2BYkJuzzXxhXV_8-5MYSl_pmQX-HnY.1770887401",
	device_id: "48:45:e6:cf:b7:2d"
}

export const useSettingStore = defineStore('setting', () => {
	// state - initialized with hardcoded defaults
	const sessionId = ref<string>("")
	const deviceId = ref<string>(DEFAULT_CONFIG.device_id)
	const wsUrl = ref<string>(DEFAULT_CONFIG.ws_url)
	const wsProxyUrl = ref<string>(DEFAULT_CONFIG.ws_proxy_url)
	const otaVersionUrl = ref<string>(DEFAULT_CONFIG.ota_version_url)
	const backendUrl = ref<string>(DEFAULT_CONFIG.backend_url)
	const tokenEnable = ref<boolean>(DEFAULT_CONFIG.token_enable)
	const token = ref<string>(DEFAULT_CONFIG.token)
	const visible = ref<boolean>(false)
	
	const configRefMap: Record<string, Ref<string | boolean>> = {
		ws_url: wsUrl,
		ws_proxy_url: wsProxyUrl,
		ota_version_url: otaVersionUrl,
		backend_url: backendUrl,
		token_enable: tokenEnable,
		token: token,
		device_id: deviceId
	}

	const fetchConfig = async (): Promise<boolean> => {
		try {
			const response = await fetch(backendUrl.value + "/config")
			const jsonData = await response.json()
			console.log("[useSettingStore][fetchConfig] response: ", jsonData)
			if (!response.ok) {
				throw new Error("Failed to fetch config")
			}
			const { data } = jsonData as { data: ConfigData }
			Object.entries(configRefMap).forEach(([key, ref]) => {
				const value = data[key]
				if (value !== undefined && value !== null) {
					ref.value = value
				}
			})
			return true;
		} catch (error) {
			console.error("[useSettingStore][fetchConfig]", error)
			return false;
		}
	}

	const saveToLocal = (): boolean => {
		const configJson = {
			ws_url: wsUrl.value,
			ws_proxy_url: wsProxyUrl.value,
			ota_version_url: otaVersionUrl.value,
			backend_url: backendUrl.value,
			token_enable: tokenEnable.value,
			token: token.value,
			device_id: deviceId.value
		}
		const dataOK = Object.values(configJson).every(value => value !== "")
		if (dataOK) {
			localStorage.setItem('settings', JSON.stringify(configJson))
			console.log("[useSettingStore][saveToLocal] 配置文件更新成功", configJson)
		} else {
			console.warn("[useSettingStore][saveToLocal] 配置文件数据不完整，未保存", configJson)
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
			console.log("[useSettingStore][loadFromLocal] 配置文件加载成功")
			return true
		}
		console.log("[useSettingStore][loadFromLocal] 配置文件不存在")
		return false
	}

	const destoryLocal = () => {
		localStorage.removeItem('settings')
		console.log("[useSettingStore][destoryLocal] 本地缓存配置文件已删除")
	}

	return {
		sessionId,
		deviceId,
		wsUrl,
		wsProxyUrl,
		otaVersionUrl,
		backendUrl,
		tokenEnable,
		token,
		visible,
		updateConfig,
		fetchConfig,
		saveToLocal,
		loadFromLocal,
		destoryLocal,
	}
})

