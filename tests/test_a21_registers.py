from dataclasses import replace
import sys
from pathlib import Path

import pytest

sys.path.insert(
    0, str(Path(__file__).resolve().parents[1] / "custom_components" / "ecovent_v2")
)

from a21_registers import (  # noqa: E402
    A21_IDENTITY_REGISTER,
    A21_IDENTITY_VALUE,
    Access,
    FilterTimer,
    Firmware,
    Kind,
    REGISTERS,
    RtcCalendar,
    RtcTime,
    Runtime,
    ScheduleEnd,
    SchedulePeriod,
    Table,
    Timer,
    _indexes,
    decode,
    encode,
    get_by_address,
    get_register,
)


def test_complete_published_surface_and_identity():
    assert A21_IDENTITY_REGISTER.table is Table.INPUT_REGISTER
    assert (A21_IDENTITY_REGISTER.address, A21_IDENTITY_VALUE) == (37, 1)
    expected = {
        Table.COIL: range(26),
        Table.DISCRETE_INPUT: range(72),
        Table.INPUT_REGISTER: range(54),
        Table.HOLDING_REGISTER: range(183),
    }
    for table, addresses in expected.items():
        assert {
            a for (t, a) in __import__("a21_registers").BY_TABLE_ADDRESS if t is table
        } == set(addresses)
    assert len([r for r in REGISTERS if r.table is Table.COIL]) == 26
    assert len([r for r in REGISTERS if r.table is Table.DISCRETE_INPUT]) == 72
    assert get_by_address(Table.HOLDING_REGISTER, 125).key == "HR_ENGINEER_PWD"
    assert get_register("DI_AlarmCODE52").address == 71
    assert get_register("HR_SetWEEK_Su_P4_END").address == 181


@pytest.mark.parametrize(
    "kind,value,words",
    [
        (Kind.BOOL, True, (1,)),
        (Kind.U8, 255, (255,)),
        (Kind.U16, 65535, (65535,)),
        (Kind.S16, -2, (65534,)),
        (Kind.TENTHS_S16, -25.0, (65286,)),
        (Kind.BYTE_PAIR, (12, 34), (3106,)),
        (Kind.TIMER, Timer(4, 5, 6), (1286, 4)),
        (Kind.FILTER_TIMER, FilterTimer(365, 23, 59), (5947, 365)),
        (Kind.RUNTIME, Runtime(42, 23, 59), (5947, 42)),
        (Kind.FIRMWARE, Firmware(1, 2, 3, 4, 2026), (258, 772, 2026)),
        (Kind.RTC_TIME, RtcTime(23, 59, 58), (15162, 23)),
        (Kind.RTC_CALENDAR, RtcCalendar(31, 4, 12, 26), (7940, 3098)),
        (Kind.PASSWORD, "1234", (12594, 13108)),
        (Kind.SCHEDULE_SPEED_TEMP, SchedulePeriod(5, 23), (1303,)),
        (Kind.SCHEDULE_END, ScheduleEnd(23, 59), (5947,)),
    ],
)
def test_all_pure_codecs_roundtrip(kind, value, words):
    assert encode(kind, value) == words
    assert decode(kind, words) == value


def test_permissions_ranges_and_bad_records_reject():
    with pytest.raises(PermissionError):
        get_register("IR_DeviceTYPE").encode(1)
    with pytest.raises(PermissionError):
        get_register("HR_DEF_SetTemp").encode(5)
    with pytest.raises(ValueError):
        get_register("HR_SetTEMP").encode(999)
    with pytest.raises(ValueError):
        encode(Kind.PASSWORD, "ABCDE")
    with pytest.raises(ValueError):
        encode(Kind.RTC_TIME, RtcTime(24, 0, 0))
    with pytest.raises(ValueError):
        decode(Kind.BOOL, (2,))


def test_register_decode_validates_structures_and_published_scalar_limits():
    with pytest.raises(ValueError, match="outside documented range"):
        get_register("IR_CurRH_Int").decode((101,))
    with pytest.raises(ValueError, match="outside documented allowed ranges"):
        get_register("HR_SetFILTER_TIMER").decode((69,))
    with pytest.raises(ValueError, match="hours must be 0..23"):
        get_register("HR_RTC_TIME").decode((0, 24))
    with pytest.raises(ValueError, match="day 31"):
        get_register("HR_RTC_CALENDAR").decode((0x1F01, 0x041A))
    with pytest.raises(ValueError, match="weekday does not match"):
        get_register("HR_RTC_CALENDAR").decode((0x1701, 0x041A))
    with pytest.raises(ValueError, match="day 31"):
        get_register("IR_VerMAIN_FMW").decode((0x0102, 0x1F04, 2026))


def test_register_decode_rejects_unknown_enum_value_within_numeric_range():
    spec = get_register("HR_OPERATION_MODE")
    assert spec.enum is not None
    restricted = replace(spec, enum={0: "off", 2: "on"})
    with pytest.raises(ValueError, match="no documented enum value"):
        restricted.decode((1,))
    with pytest.raises(ValueError, match="no documented enum value"):
        restricted.encode(1)


def test_bypass_rotor_type_preserves_the_pdf_maximum_discrepancy():
    spec = get_register("HR_BPS_ROTOR_TYPE")
    assert spec.maximum == 5
    assert spec.enum[5] == "three-point bypass"
    assert "numeric maximum is 4" in spec.source_note


def test_pdf_specific_holding_metadata_has_no_generic_fallback_ranges():
    # 0..255 is published only for speed mode and fan-alarm control, not a
    # generic default for the many byte-sized holding registers.
    generic = [
        spec.key
        for spec in REGISTERS
        if spec.table is Table.HOLDING_REGISTER and spec.maximum == 255
    ]
    assert generic == ["HR_SPEED_MODE", "HR_FanAlarmCTRL"]
    temp = get_register("HR_SetTEMP")
    assert (temp.minimum, temp.maximum, temp.default, temp.unit) == (15, 30, 23, "°C")
    assert get_register("HR_SetCO2").maximum == 2000
    assert get_register("HR_RTC_TIME").default is None


def test_index_validation_rejects_duplicates_and_overlaps():
    one = get_register("CL_POWER")
    with pytest.raises(ValueError, match="duplicate key"):
        _indexes((one, one))
    overlap = one.__class__(
        "other", Table.COIL, 0, Access.READ_ONLY, Kind.BOOL, "overlap"
    )
    with pytest.raises(ValueError, match="overlap"):
        _indexes((one, overlap))
