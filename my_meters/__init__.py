"""The My Meters integration."""
import logging
import aiohttp
from datetime import timedelta
from yarl import URL

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)
from homeassistant.util import dt as dt_util

from .const import DOMAIN, CONF_API_URL, CONF_TOKEN, DEFAULT_SCAN_INTERVAL

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["sensor"]

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Настройка интеграции."""

    api_url = entry.data[CONF_API_URL]
    token = entry.data[CONF_TOKEN]

    async def async_update_data():
        """Скачивает данные с правильным форматом времени."""
        
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        # --- ФОРМИРОВАНИЕ ПРАВИЛЬНОГО URL ---
        # 1. Берем базовый URL
        url_obj = URL(api_url)
        
        # 2. Получаем текущее время
        now = dt_util.now()
        
        # 3. Форматируем строго под RFC3339 (как требует Go)
        # timespec='seconds' убирает микросекунды (было .999999, станет ровно :05)
        # Это даст строку вида: "2026-02-11T12:00:00+03:00"
        now_str = now.isoformat(timespec='seconds')
        
        # 4. Подменяем параметр в URL
        # yarl сам закодирует двоеточия и плюсы в %3A и %2B
        new_url = url_obj.update_query({"filter.endSyncedAt": now_str})

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(new_url, headers=headers) as resp:
                    if resp.status != 200:
                        # Читаем текст ошибки, чтобы видеть детали в логах
                        err_text = await resp.text()
                        raise UpdateFailed(f"Ошибка API {resp.status}: {err_text}")
                    
                    data = await resp.json()

                    parsed_data = {}
                    if isinstance(data, list):
                        for item in data:
                            meter_data = item.get("result", {}).get("data", {})
                            if meter_data:
                                ind_id = meter_data.get("indicatorId")
                                parsed_data[ind_id] = meter_data
                    else:
                        _LOGGER.warning("Неожиданный формат данных (ожидался список)")

                    return parsed_data

        except Exception as err:
            raise UpdateFailed(f"Ошибка соединения: {err}")

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name="my_meters_coordinator",
        update_method=async_update_data,
        update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
    )

    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(update_listener))

    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok

async def update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)