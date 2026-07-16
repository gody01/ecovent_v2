"""VENTS A21 Modbus catalogue (V55-8-1EN-02).

Addresses in this module are zero based Modbus PDU addresses.  The catalogue is
the published A21 surface, not the BGCP/UDP map: A21 is identified by input
register 37 being ``1``.  In particular, BGCP parameter 0x00B9 is unrelated.

All multi-byte values use ordinary Modbus word order.  The ECONOPRIME hardware
byte order has not been captured, so do not infer a device-specific byte swap
from this documentation alone.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Iterable, Mapping


class Table(str, Enum):
    COIL = "coil"
    DISCRETE_INPUT = "discrete_input"
    INPUT_REGISTER = "input_register"
    HOLDING_REGISTER = "holding_register"


class Access(str, Enum):
    READ_ONLY = "R"
    WRITE_ONLY = "W"
    READ_WRITE = "R/W"

    @property
    def readable(self) -> bool:
        return self is not Access.WRITE_ONLY

    @property
    def writable(self) -> bool:
        return self is not Access.READ_ONLY


class Kind(str, Enum):
    BOOL = "bool"
    U8 = "u8"
    U16 = "u16"
    S16 = "s16"
    TENTHS_S16 = "tenths_s16"
    BYTE_PAIR = "byte_pair"
    TIMER = "timer"
    FILTER_TIMER = "filter_timer"
    RUNTIME = "runtime"
    FIRMWARE = "firmware"
    RTC_TIME = "rtc_time"
    RTC_CALENDAR = "rtc_calendar"
    PASSWORD = "password"
    SCHEDULE_SPEED_TEMP = "schedule_speed_temp"
    SCHEDULE_END = "schedule_end"


@dataclass(frozen=True)
class Timer:
    hours: int
    minutes: int
    seconds: int = 0


@dataclass(frozen=True)
class FilterTimer:
    days: int
    hours: int
    minutes: int


@dataclass(frozen=True)
class Runtime:
    days: int
    hours: int
    minutes: int


@dataclass(frozen=True)
class Firmware:
    major: int
    minor: int
    day: int
    month: int
    year: int


@dataclass(frozen=True)
class RtcTime:
    hours: int
    minutes: int
    seconds: int


@dataclass(frozen=True)
class RtcCalendar:
    day: int
    weekday: int
    month: int
    year: int


@dataclass(frozen=True)
class SchedulePeriod:
    speed: int
    temperature: int


@dataclass(frozen=True)
class ScheduleEnd:
    hour: int
    minute: int


def _word(value: Any) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or not 0 <= value <= 0xFFFF:
        raise ValueError(f"not a Modbus word: {value!r}")
    return value


def _byte(value: int, name: str = "byte") -> int:
    if not isinstance(value, int) or isinstance(value, bool) or not 0 <= value <= 0xFF:
        raise ValueError(f"{name} must be 0..255")
    return value


def _range(value: int, low: int, high: int, name: str) -> int:
    if not low <= value <= high:
        raise ValueError(f"{name} must be {low}..{high}")
    return value


def _pair(high: int, low: int) -> int:
    return (_byte(high, "high byte") << 8) | _byte(low, "low byte")


def _unpair(word: int) -> tuple[int, int]:
    word = _word(word)
    return word >> 8, word & 0xFF


def decode(kind: Kind, words: Iterable[int]) -> Any:
    """Decode one catalogue value from standard-order Modbus words."""
    ws = tuple(_word(w) for w in words)
    needed = 2 if kind in {Kind.TIMER, Kind.FILTER_TIMER, Kind.RUNTIME, Kind.RTC_TIME, Kind.RTC_CALENDAR, Kind.PASSWORD} else 3 if kind is Kind.FIRMWARE else 1
    if len(ws) != needed:
        raise ValueError(f"{kind.value} requires {needed} words, got {len(ws)}")
    w = ws[0]
    if kind is Kind.BOOL:
        if w not in (0, 1): raise ValueError("bool word must be 0 or 1")
        return bool(w)
    if kind is Kind.U8: return _range(w, 0, 255, "u8")
    if kind is Kind.U16: return w
    if kind is Kind.S16: return w - 0x10000 if w & 0x8000 else w
    if kind is Kind.TENTHS_S16:
        value = w - 0x10000 if w & 0x8000 else w
        return value / 10
    if kind is Kind.BYTE_PAIR: return _unpair(w)
    if kind is Kind.TIMER:
        minute, second = _unpair(ws[0]); _, hour = _unpair(ws[1]); return Timer(hour, minute, second)
    if kind is Kind.FILTER_TIMER:
        hour, minute = _unpair(ws[0]); return FilterTimer(ws[1], hour, minute)
    if kind is Kind.RUNTIME:
        hour, minute = _unpair(ws[0]); return Runtime(ws[1], hour, minute)
    if kind is Kind.FIRMWARE:
        major, minor = _unpair(ws[0]); day, month = _unpair(ws[1]); return Firmware(major, minor, day, month, ws[2])
    if kind is Kind.RTC_TIME:
        minute, second = _unpair(ws[0]); _, hour = _unpair(ws[1]); return RtcTime(hour, minute, second)
    if kind is Kind.RTC_CALENDAR:
        day, weekday = _unpair(ws[0]); month, year = _unpair(ws[1]); return RtcCalendar(day, weekday, month, year)
    if kind is Kind.PASSWORD:
        chars = bytes(_unpair(ws[0]) + _unpair(ws[1])); return chars.split(b"\0", 1)[0].decode("ascii")
    if kind is Kind.SCHEDULE_SPEED_TEMP:
        speed, temp = _unpair(w); return SchedulePeriod(speed, temp)
    if kind is Kind.SCHEDULE_END:
        hour, minute = _unpair(w); return ScheduleEnd(hour, minute)
    raise AssertionError(kind)


def encode(kind: Kind, value: Any) -> tuple[int, ...]:
    """Encode a value to Modbus words, validating the documented record shape."""
    if kind is Kind.BOOL:
        if not isinstance(value, bool): raise ValueError("bool required")
        return (int(value),)
    if kind is Kind.U8: return (_byte(value),)
    if kind is Kind.U16: return (_word(value),)
    if kind is Kind.S16:
        _range(value, -32768, 32767, "s16"); return (value & 0xFFFF,)
    if kind is Kind.TENTHS_S16:
        raw = round(value * 10)
        if raw != value * 10: raise ValueError("tenths value must have one decimal place")
        _range(raw, -32768, 32767, "tenths_s16"); return (raw & 0xFFFF,)
    if kind is Kind.BYTE_PAIR:
        high, low = value; return (_pair(high, low),)
    if kind in {Kind.TIMER, Kind.RTC_TIME}:
        cls = Timer if kind is Kind.TIMER else RtcTime
        if not isinstance(value, cls): raise ValueError(f"{kind.value} record required")
        return (_pair(_range(value.minutes, 0, 59, "minutes"), _range(value.seconds, 0, 59, "seconds")), _pair(0, _range(value.hours, 0, 23, "hours")))
    if kind is Kind.FILTER_TIMER:
        if not isinstance(value, FilterTimer): raise ValueError("filter timer record required")
        return (_pair(_range(value.hours, 0, 23, "hours"), _range(value.minutes, 0, 59, "minutes")), _range(value.days, 0, 365, "days"))
    if kind is Kind.RUNTIME:
        if not isinstance(value, Runtime): raise ValueError("runtime record required")
        return (_pair(_range(value.hours, 0, 23, "hours"), _range(value.minutes, 0, 59, "minutes")), _word(value.days))
    if kind is Kind.FIRMWARE:
        if not isinstance(value, Firmware): raise ValueError("firmware record required")
        return (_pair(value.major, value.minor), _pair(_range(value.day, 1, 31, "day"), _range(value.month, 1, 12, "month")), _word(value.year))
    if kind is Kind.RTC_CALENDAR:
        if not isinstance(value, RtcCalendar): raise ValueError("calendar record required")
        return (_pair(_range(value.day, 1, 31, "day"), _range(value.weekday, 1, 7, "weekday")), _pair(_range(value.month, 1, 12, "month"), _range(value.year, 0, 99, "year")))
    if kind is Kind.PASSWORD:
        if not isinstance(value, str) or not 1 <= len(value) <= 4 or not value.isascii() or not value.isdigit(): raise ValueError("password must be 1-4 ASCII digits")
        raw = value.encode().ljust(4, b"\0"); return ((raw[0] << 8) | raw[1], (raw[2] << 8) | raw[3])
    if kind is Kind.SCHEDULE_SPEED_TEMP:
        if not isinstance(value, SchedulePeriod): raise ValueError("schedule period required")
        return (_pair(_range(value.speed, 0, 5, "speed"), _range(value.temperature, 0, 30, "temperature")),)
    if kind is Kind.SCHEDULE_END:
        if not isinstance(value, ScheduleEnd): raise ValueError("schedule end required")
        return (_pair(_range(value.hour, 0, 23, "hour"), _range(value.minute, 0, 59, "minute")),)
    raise AssertionError(kind)


@dataclass(frozen=True)
class RegisterSpec:
    key: str
    table: Table
    address: int
    access: Access
    kind: Kind
    description: str
    minimum: int | None = None
    maximum: int | None = None
    unit: str | None = None
    word_count: int = 1
    enum: Mapping[int, str] | None = None
    source_note: str | None = None

    def decode(self, words: Iterable[int]) -> Any:
        return decode(self.kind, words)

    def encode(self, value: Any) -> tuple[int, ...]:
        if not self.access.writable: raise PermissionError(f"{self.key} is read-only")
        words = encode(self.kind, value)
        if self.minimum is not None and self.kind in {Kind.U8, Kind.U16, Kind.S16, Kind.TENTHS_S16}:
            numeric = value * 10 if self.kind is Kind.TENTHS_S16 else value
            if not self.minimum <= numeric <= self.maximum: raise ValueError(f"{self.key} outside documented range")
        return words


def _spec(key: str, table: Table, address: int, access: Access, kind: Kind, description: str, minimum: int | None = None, maximum: int | None = None, unit: str | None = None, word_count: int = 1, enum: Mapping[int, str] | None = None, source_note: str | None = None) -> RegisterSpec:
    return RegisterSpec(key, table, address, access, kind, description, minimum, maximum, unit, word_count, enum, source_note)


_COILS = [
    ("CL_POWER", "Unit On/Off"), ("CL_TIMER", "Main timer"), ("CL_WEEK", "Weekly Schedule"), ("CL_Boost_MODE", "Boost mode"), ("CL_FPLC_MODE", "Fireplace mode"),
    ("CL_IntRH_CTRL", "Main humidity sensor activation"), ("CL_ExtRH_CTRL", "External humidity sensor activation"), ("CL_IntCO2_CTRL", "Main CO2 sensor activation"), ("CL_ExtCO2_CTRL", "External CO2 sensor activation"), ("CL_IntPM2_5_CTRL", "Main PM2.5 sensor activation"),
    ("CL_ExtPM2_5_CTRL", "External PM2.5 sensor activation"), ("CL_IntVOC_CTRL", "Main VOC sensor activation"), ("CL_ExtVOC_CTRL", "External VOC sensor activation"), ("CL_BoostSWITCH_CTRL", "Boost switch input activation"), ("CL_FplcSWITCH_CTRL", "Fireplace switch input activation"),
    ("CL_FireALARM_CTRL", "Fire alarm sensor activation"), ("CL_10V_SENSOR_CTRL", "External 0-10 V input activation"), ("CL_RESET_FILTER_TIMER", "Reset filter timer"), ("CL_RESET_ALARM", "Reset all alarms"), ("CL_RESTORE_FACTORY", "Restore factory settings"),
    ("CL_CLOUD_CTRL", "Cloud control activation"), ("CL_MinSuAirOutTEMP_CTRL", "Minimum supply air temperature control"), ("CL_WaterPRESS_CTRL", "Heat medium water pressure sensor activation"), ("CL_WaterFLOW_CTRL", "Heat medium water flow sensor activation"), ("CL_WaterHeaterAutoRestart", "Automatic restart after return-water emergency"), ("CL_AutoReductionAirFlow", "Automatic air-flow reduction on main heater failure"),
]
_DI_BASE = ["DI_CurBoostSWITCH", "DI_CurFplcSWITCH", "DI_CurFireALARM", "DI_StatusRH", "DI_StatusCO2", "DI_StatusPM2_5", "DI_StatusVOC", "DI_StatusHEATER", "DI_StatusCOOLER", "DI_StatusFanBLOWING", "DI_CurPreHeaterThermostat", "DI_CurMainHeaterThermostat", "DI_CurSuFilterPRESS", "DI_CurExFilterPRESS", "DI_CurWaterPRESS", "DI_CurWaterFLOW", "DI_CurSuFanPRESS", "DI_CurExFanPRESS", "DI_WaterPreheatingStatus"]
_IR = [
    ("IR_CurSelTEMP", Kind.TENTHS_S16, -32768, 32767, "°C"), ("IR_CurTEMP_SuAirIn", Kind.TENTHS_S16, -32768, 32767, "°C"), ("IR_CurTEMP_SuAirOut", Kind.TENTHS_S16, -32768, 32767, "°C"), ("IR_CurTEMP_ExAirIn", Kind.TENTHS_S16, -32768, 32767, "°C"), ("IR_CurTEMP_ExAirOut", Kind.TENTHS_S16, -32768, 32767, "°C"), ("IR_CurTEMP_Ext", Kind.TENTHS_S16, -32768, 32767, "°C"), ("IR_CurTEMP_AfterPreHeater", Kind.TENTHS_S16, -32768, 32767, "°C"), ("IR_CurTEMP_BeforeMainHeater", Kind.TENTHS_S16, -32768, 32767, "°C"), ("IR_CurTEMP_Water", Kind.TENTHS_S16, -32768, 32767, "°C"), ("IR_CurVBAT", Kind.U16, 0, 5000, "mV"),
    ("IR_CurRH_Int", Kind.U8, 0, 100, "%"), ("IR_CurRH_Ext", Kind.U8, 0, 100, "%"), ("IR_CurCO2_Int", Kind.U16, 0, 10000, "ppm"), ("IR_CurCO2_Ext", Kind.U16, 0, 10000, "ppm"), ("IR_CurPM2_5_Int", Kind.U16, 0, 1000, "µg/m³"), ("IR_CurPM2_5_Ext", Kind.U16, 0, 1000, "µg/m³"), ("IR_CurVOC_Int", Kind.U8, 0, 100, "%"), ("IR_CurVOC_Ext", Kind.U8, 0, 100, "%"), ("IR_Cur10V_SENSOR", Kind.U16, 0, 100, "%"), ("IR_CurSuAirFLOW", Kind.U16, 0, 10000, "m³/h"), ("IR_CurExAirFLOW", Kind.U16, 0, 10000, "m³/h"), ("IR_CurSuPRESS", Kind.U16, 0, 10000, "Pa"), ("IR_CurExPRESS", Kind.U16, 0, 10000, "Pa"), ("IR_SuRPM", Kind.U16, 0, 5000, "rpm"), ("IR_ExRPM", Kind.U16, 0, 5000, "rpm"),
]


def _catalogue() -> tuple[RegisterSpec, ...]:
    out: list[RegisterSpec] = []
    for address, (key, text) in enumerate(_COILS):
        access = Access.WRITE_ONLY if address in (17, 18, 19) else Access.READ_ONLY if address in (3, 4) else Access.READ_WRITE
        out.append(_spec(key, Table.COIL, address, access, Kind.BOOL, text, 1 if access is Access.WRITE_ONLY else 0, 1, None))
    out.extend(_spec(key, Table.DISCRETE_INPUT, address, Access.READ_ONLY, Kind.BOOL, key.replace("DI_", "").replace("_", " "), 0, 1) for address, key in enumerate(_DI_BASE))
    out.extend(_spec(f"DI_AlarmCODE{address - 19}", Table.DISCRETE_INPUT, address, Access.READ_ONLY, Kind.BOOL, f"Alarm indicator with code No. {address - 19}", 0, 1) for address in range(19, 72))
    for address, (key, kind, low, high, unit) in enumerate(_IR): out.append(_spec(key, Table.INPUT_REGISTER, address, Access.READ_ONLY, kind, key[3:].replace("_", " "), low, high, unit))
    out += [_spec("IR_CurTIMER_TIME", Table.INPUT_REGISTER, 25, Access.READ_ONLY, Kind.TIMER, "Current countdown time of main timer", word_count=2), _spec("IR_CurFILTER_TIMER", Table.INPUT_REGISTER, 27, Access.READ_ONLY, Kind.FILTER_TIMER, "Filter replacement timer countdown", word_count=2), _spec("IR_TotalWorkingTime", Table.INPUT_REGISTER, 29, Access.READ_ONLY, Kind.RUNTIME, "Motor hours", word_count=2), _spec("IR_StateFILTER", Table.INPUT_REGISTER, 31, Access.READ_ONLY, Kind.U8, "Filter condition", 0, 3, enum={0:"clean",1:"supply clogged",2:"extract clogged",3:"both/timer"}), _spec("IR_CurWeekSpeed", Table.INPUT_REGISTER, 32, Access.READ_ONLY, Kind.U8, "Weekly schedule speed", 0, 5), _spec("IR_CurWeekSetTemp", Table.INPUT_REGISTER, 33, Access.READ_ONLY, Kind.U8, "Weekly schedule temperature", 0, 30, "°C"), _spec("IR_VerMAIN_FMW", Table.INPUT_REGISTER, 34, Access.READ_ONLY, Kind.FIRMWARE, "Firmware version and creation date", word_count=3), _spec("IR_DeviceTYPE", Table.INPUT_REGISTER, 37, Access.READ_ONLY, Kind.U16, "Controller type; 1 is A21", 0, 65535), _spec("IR_ALARM", Table.INPUT_REGISTER, 38, Access.READ_ONLY, Kind.U8, "Alarm/warning indicator", 0, 2, enum={0:"none",1:"alarm",2:"warning"})]
    for address, key in enumerate(["IR_RH_U", "IR_CO2_U", "IR_PM2_5_U", "IR_VOC_U", "IR_PreHeater_U", "IR_MainHeater_U", "IR_BPS_ROTOR_U", "IR_KKB_U", "IR_ReturnWater_U", "IR_SuAirOutSetTemp", "IR_WaterStandbySetTemp", "IR_WaterStartSetTemp", "IR_StatusBpsRotor", "IR_CurSuFanSpeed", "IR_CurExFanSpeed"], 39):
        kind = Kind.TENTHS_S16 if address in (48,49,50) else Kind.U8; out.append(_spec(key, Table.INPUT_REGISTER, address, Access.READ_ONLY, kind, key[3:].replace("_", " ")))
    hr_names = ["HR_VENTILATION_MODE","HR_MaxSPEED_MODE","HR_SPEED_MODE","HR_MinSPEED","HR_MaxSPEED","HR_SuSPEED0","HR_ExSPEED0","HR_SuSPEED1","HR_ExSPEED1","HR_SuSPEED2","HR_ExSPEED2","HR_SuSPEED3","HR_ExSPEED3","HR_SuSPEED4","HR_ExSPEED4","HR_SuSPEED5","HR_ExSPEED5","HR_ManualSPEED","HR_BlowingSPEED","HR_Boost_SuSPEED","HR_Boost_ExSPEED","HR_FPLC_SuSPEED","HR_FPLC_ExSPEED","HR_MinAirFLOW","HR_MaxAirFLOW"]
    hr_names += [f"HR_{side}SPEED{speed}_FLOW" for speed in range(0,6) for side in ("Su","Ex")]
    hr_names += ["HR_MinAirPRESS","HR_MaxAirPRESS","HR_SuSPEED0_PRESS","HR_ExSPEED0_PRESS","HR_SuSPEED1_PRESS","HR_ExSPEED1_PRESS","HR_OPERATION_MODE","HR_SetTEMP","HR_SetRH","HR_SetCO2","HR_SetPM2_5","HR_SetVOC","HR_TIMER_MODE","HR_SetTIMER_TEMP","HR_SetTIMER_TIME","HR_SetTEMP_WinterSummer","HR_SelTEMP_SENSOR","HR_MainHEATER_TYPE","HR_COOLER_TYPE","HR_DEF_MODE","HR_BPS_ROTOR_TYPE","HR_SetFILTER_TIMER","HR_BoostDelaySwitchingOff","HR_BoostDelaySwitchingOn"]
    for address, key in enumerate(hr_names):
        ro = address in {0,1,3,4,23,24,37,38,57}; kind = Kind.U16 if address in set(range(23,43)) | {46,58} else Kind.U8
        low, high = (0,10000) if kind is Kind.U16 else (0,255)
        if address == 57:
            # V55-8-1EN-02's maximum column says 4, while its explicit list
            # continues with 5 (three-point bypass).  Preserve that discrepancy
            # instead of silently losing the documented enum member.
            high = 5
            enum = {0: "not available", 1: "two-point bypass", 2: "analogue bypass", 3: "discrete rotary", 4: "analogue rotary", 5: "three-point bypass"}
            note = "V55-8-1EN-02 numeric maximum is 4; its prose enum also documents value 5 (three-point bypass)."
        else:
            enum = None
            note = None
        out.append(_spec(key, Table.HOLDING_REGISTER, address, Access.READ_ONLY if ro else Access.READ_WRITE, kind, key[3:].replace("_", " "), low, high, enum=enum, source_note=note))
    out += [_spec("HR_RTC_TIME",Table.HOLDING_REGISTER,61,Access.READ_WRITE,Kind.RTC_TIME,"RTC time",word_count=2), _spec("HR_RTC_CALENDAR",Table.HOLDING_REGISTER,63,Access.READ_WRITE,Kind.RTC_CALENDAR,"RTC calendar",word_count=2)]
    for address, key in enumerate(["HR_MaxCO2_Int","HR_MaxPM2_5_Int","HR_SetMinSuAirOutTEMP","HR_MainHeaterMODE","HR_SetMainHeaterMANUAL","HR_CoolerMODE","HR_SetCoolerMANUAL","HR_PreHeaterMODE","HR_SetPreHeaterMANUAL","HR_BPS_ROTOR_MODE","HR_SetBpsRotorMANUAL"],65): out.append(_spec(key,Table.HOLDING_REGISTER,address,Access.READ_WRITE,Kind.U16 if address<67 else Kind.U8,key[3:].replace("_"," ")))
    for address, key in enumerate([f"HR_{controller}_{term}" for controller in ("RH","CO2","PM2_5","VOC","PreHeater","MainHeater","BPS_ROTOR","KKB","ReturnWater") for term in ("Kp","Ki","Kd")],76): out.append(_spec(key,Table.HOLDING_REGISTER,address,Access.READ_WRITE,Kind.U16,key[3:].replace("_"," "),0,1000))
    tail = ["HR_FanAlarmCTRL","HR_SetTimeDetectFanALARM","HR_SetTimeOpenVALVE","HR_SetTimeFanBLOWING","HR_KKB_MinTimeOFF","HR_KKB_MinTimeON","HR_KKB_HYSTERESIS","HR_BPS_Position","HR_TimeOpenBPS","HR_CorrTEMP_SuAirIn","HR_CorrTEMP_SuAirOut","HR_CorrTEMP_ExAirIn","HR_CorrTEMP_ExAirOut","HR_CorrTEMP_Water","HR_CorrTEMP_Ext","HR_WaterValveMinPos","HR_WaterMaxStartTime","HR_WaterMinStartTemp","HR_WaterMaxStartTemp","HR_WaterMinAlarmTemp","HR_WaterMaxAlarmTemp"]
    for address,key in enumerate(tail,103):
        ro=address in {103,104,110,111}; kind=Kind.S16 if address in set(range(112,118))|set(range(120,124)) else Kind.U8
        out.append(_spec(key,Table.HOLDING_REGISTER,address,Access.READ_ONLY if ro else Access.READ_WRITE,kind,key[3:].replace("_"," ")))
    out.append(_spec("HR_ENGINEER_PWD",Table.HOLDING_REGISTER,124,Access.READ_WRITE,Kind.PASSWORD,"Engineering menu password",48,57,"ASCII",2))
    days=("Mo","Tu","We","Th","Fr","Sa","Su")
    for day_no, day in enumerate(days):
        base=126+day_no*8
        for period in range(1,5):
            out.append(_spec(f"HR_SetWEEK_{day}_P{period}",Table.HOLDING_REGISTER,base+(period-1)*2,Access.READ_WRITE,Kind.SCHEDULE_SPEED_TEMP,f"{day} period {period}: speed and temperature",word_count=1))
            end_access=Access.READ_ONLY if period==4 else Access.READ_WRITE
            out.append(_spec(f"HR_SetWEEK_{day}_P{period}_END",Table.HOLDING_REGISTER,base+(period-1)*2+1,end_access,Kind.SCHEDULE_END,f"{day} period {period} end time",word_count=1))
    out.append(_spec("HR_DEF_SetTemp",Table.HOLDING_REGISTER,182,Access.READ_ONLY,Kind.U8,"Exhaust air frost-protection temperature",4,10,"°C"))
    return tuple(out)


REGISTERS = _catalogue()


def _indexes(registers: Iterable[RegisterSpec]) -> tuple[dict[str, RegisterSpec], dict[tuple[Table, int], RegisterSpec]]:
    keys: dict[str, RegisterSpec] = {}; addresses: dict[tuple[Table,int], RegisterSpec] = {}
    for spec in registers:
        if spec.key in keys: raise ValueError(f"duplicate key {spec.key}")
        keys[spec.key] = spec
        for address in range(spec.address, spec.address + spec.word_count):
            slot=(spec.table,address)
            if slot in addresses: raise ValueError(f"overlap at {slot}")
            addresses[slot]=spec
    return keys, addresses


BY_KEY, BY_TABLE_ADDRESS = _indexes(REGISTERS)


def get_register(key: str) -> RegisterSpec:
    return BY_KEY[key]


def get_by_address(table: Table, address: int) -> RegisterSpec:
    return BY_TABLE_ADDRESS[(table, address)]


A21_IDENTITY_REGISTER = BY_KEY["IR_DeviceTYPE"]
A21_IDENTITY_VALUE = 1
