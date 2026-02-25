"""Platform for sensor integration."""
from homeassistant.components.sensor import (
    SensorEntity,
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Настройка сенсоров."""
    coordinator = hass.data[DOMAIN][entry.entry_id]

    sensors = []
    for indicator_id, data in coordinator.data.items():
        sensors.append(MyMeterSensor(coordinator, indicator_id, data))

    async_add_entities(sensors)


class MyMeterSensor(CoordinatorEntity, SensorEntity):
    """Описание одного сенсора."""

    def __init__(self, coordinator, indicator_id, initial_data):
        """Инициализация."""
        super().__init__(coordinator)
        self._indicator_id = indicator_id
        self._metric_type = initial_data.get("metricType")
        self._unit_type = initial_data.get("unitType")
        self._device_model = initial_data.get("deviceModel")
        
        # Уникальный ID
        self._attr_unique_id = f"meter_{indicator_id}"
        
        # Имя сенсора
        friendly_type = "Счетчик"
        if self._metric_type == "ELECTRICITY":
            friendly_type = "Электричество"
        elif self._metric_type == "HOT_WATER":
            friendly_type = "Горячая вода"
        elif self._metric_type == "COLD_WATER":
            friendly_type = "Холодная вода"
            
        self._attr_name = f"{friendly_type} ({indicator_id})"

    @property
    def device_info(self):
        """Информация об устройстве."""
        return {
            "identifiers": {(DOMAIN, str(self._indicator_id))},
            "name": self._attr_name,
            "model": self._device_model,
            "manufacturer": "My Management Co",
        }

    @property
    def native_value(self):
        """Текущее значение с учетом корректировки."""
        # Получаем "сырые" данные от API
        data = self.coordinator.data.get(self._indicator_id, {})
        raw_value = data.get("value")

        if raw_value is None:
            return None

        # Получаем корректировку из настроек (options). 
        # Ключ - это ID счетчика в виде строки. По умолчанию 0.0.
        correction = self.coordinator.config_entry.options.get(str(self._indicator_id), 0.0)
        
        # Возвращаем сумму
        return float(raw_value) + float(correction)
        

    @property
    def extra_state_attributes(self):
        """Доп. атрибуты."""
        data = self.coordinator.data.get(self._indicator_id, {})
        return {
            "synced_at": data.get("syncedAt"),
            "fias_id": data.get("fiasId")
        }

    @property
    def native_unit_of_measurement(self):
        """Единицы измерения."""
        if self._unit_type == "KWH":
            return "kWh"
        if self._unit_type == "M3":
            return "m³"
        return self._unit_type

    # --- ВОТ ЭТОТ НОВЫЙ БЛОК ОТВЕЧАЕТ ЗА ИКОНКИ ---
    @property
    def icon(self):
        """Иконка в зависимости от типа."""
        if self._metric_type == "ELECTRICITY":
            return "mdi:flash"             # Желтая молния
        if self._metric_type == "HOT_WATER":
            return "mdi:water-thermometer" # Градусник в воде
        if self._metric_type == "COLD_WATER":
            return "mdi:water"             # Капля воды
        return "mdi:counter"               # Стандартная иконка, если тип неизвестен
    # ----------------------------------------------

    @property
    def device_class(self):
        """Класс устройства."""
        if self._metric_type == "ELECTRICITY":
            return SensorDeviceClass.ENERGY
        if "WATER" in str(self._metric_type):
            return SensorDeviceClass.WATER
        return None

    @property
    def state_class(self):
        """Класс состояния для статистики."""
        return SensorStateClass.TOTAL_INCREASING