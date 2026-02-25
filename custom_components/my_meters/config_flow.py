"""Config flow for My Meters integration."""
import logging
import voluptuous as vol
import aiohttp

from homeassistant import config_entries
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult

from .const import DOMAIN, CONF_API_URL, CONF_TOKEN

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_API_URL, default="https://api.doma.ai/v1/meters"): str,
        vol.Required(CONF_TOKEN): str,
    }
)

async def validate_input(hass: HomeAssistant, data: dict) -> dict:
    """Проверка токена."""
    headers = {"Authorization": f"Bearer {data[CONF_TOKEN]}"}
    async with aiohttp.ClientSession() as session:
        async with session.get(data[CONF_API_URL], headers=headers) as resp:
            if resp.status != 200:
                raise ValueError(f"Status code: {resp.status}")
            await resp.json()
    return {"title": "Счетчики ЖКХ"}

class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Основной класс настройки."""
    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return OptionsFlowHandler(config_entry)

    async def async_step_user(self, user_input=None) -> FlowResult:
        errors = {}
        if user_input is not None:
            try:
                info = await validate_input(self.hass, user_input)
                return self.async_create_entry(title=info["title"], data=user_input)
            except Exception as e:
                _LOGGER.error("Ошибка соединения: %s", e)
                errors["base"] = "cannot_connect"

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )

class OptionsFlowHandler(config_entries.OptionsFlow):
    """Обработчик кнопки 'Настроить'."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Инициализация."""
        # ВАЖНО: Мы сохраняем entry в переменную self._config_entry (с подчеркиванием),
        # чтобы не конфликтовать с self.config_entry родительского класса.
        self._config_entry = config_entry

    async def async_step_init(self, user_input=None) -> FlowResult:
        """Показываем форму настроек."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        schema = {}
        # Безопасно получаем координатора
        coordinator = self.hass.data.get(DOMAIN, {}).get(self._config_entry.entry_id)

        if coordinator and coordinator.data:
            for indicator_id, data in coordinator.data.items():
                field_key = str(indicator_id)
                # Берем текущее значение из сохраненных опций
                current_val = self._config_entry.options.get(field_key, 0.0)
                
                m_type = data.get("metricType", "Unknown")
                label = f"Коррекция: {m_type} ({indicator_id})"
                
                schema[vol.Optional(field_key, default=current_val)] = vol.Coerce(float)
        
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(schema)
        )
        