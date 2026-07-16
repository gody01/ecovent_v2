import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "custom_components" / "ecovent_v2"))

from a21_registers import (
    A21_IDENTITY_REGISTER, A21_IDENTITY_VALUE, Access, FilterTimer, Firmware,
    Kind, REGISTERS, RtcCalendar, RtcTime, Runtime, ScheduleEnd, SchedulePeriod,
    Table, Timer, _indexes, decode, encode, get_by_address, get_register,
)


def test_complete_published_surface_and_identity():
    assert A21_IDENTITY_REGISTER.table is Table.INPUT_REGISTER
    assert (A21_IDENTITY_REGISTER.address, A21_IDENTITY_VALUE) == (37, 1)
    expected = {Table.COIL: range(26), Table.DISCRETE_INPUT: range(72), Table.INPUT_REGISTER: range(54), Table.HOLDING_REGISTER: range(183)}
    for table, addresses in expected.items():
        assert {a for (t, a) in __import__("a21_registers").BY_TABLE_ADDRESS if t is table} == set(addresses)
    assert len([r for r in REGISTERS if r.table is Table.COIL]) == 26
    assert len([r for r in REGISTERS if r.table is Table.DISCRETE_INPUT]) == 72
    assert get_by_address(Table.HOLDING_REGISTER, 125).key == "HR_ENGINEER_PWD"
    assert get_register("DI_AlarmCODE52").address == 71
    assert get_register("HR_SetWEEK_Su_P4_END").address == 181


@pytest.mark.parametrize("kind,value,words", [
    (Kind.BOOL, True, (1,)), (Kind.U8, 255, (255,)), (Kind.U16, 65535, (65535,)),
    (Kind.S16, -2, (65534,)), (Kind.TENTHS_S16, -25.0, (65286,)), (Kind.BYTE_PAIR, (12, 34), (3106,)),
    (Kind.TIMER, Timer(4, 5, 6), (1286, 4)), (Kind.FILTER_TIMER, FilterTimer(365, 23, 59), (5947, 365)),
    (Kind.RUNTIME, Runtime(42, 23, 59), (5947, 42)), (Kind.FIRMWARE, Firmware(1,2,3,4,2026), (258,772,2026)),
    (Kind.RTC_TIME, RtcTime(23, 59, 58), (15162,23)), (Kind.RTC_CALENDAR, RtcCalendar(31,7,12,26), (7943,3098)),
    (Kind.PASSWORD, "1234", (12594,13108)), (Kind.SCHEDULE_SPEED_TEMP, SchedulePeriod(5,23), (1303,)), (Kind.SCHEDULE_END, ScheduleEnd(23,59), (5947,)),
])
def test_all_pure_codecs_roundtrip(kind, value, words):
    assert encode(kind, value) == words
    assert decode(kind, words) == value


def test_permissions_ranges_and_bad_records_reject():
    with pytest.raises(PermissionError): get_register("IR_DeviceTYPE").encode(1)
    with pytest.raises(PermissionError): get_register("HR_DEF_SetTemp").encode(5)
    with pytest.raises(ValueError): get_register("HR_SetTEMP").encode(999)
    with pytest.raises(ValueError): encode(Kind.PASSWORD, "ABCDE")
    with pytest.raises(ValueError): encode(Kind.RTC_TIME, RtcTime(24, 0, 0))
    with pytest.raises(ValueError): decode(Kind.BOOL, (2,))


def test_index_validation_rejects_duplicates_and_overlaps():
    one = get_register("CL_POWER")
    with pytest.raises(ValueError, match="duplicate key"):
        _indexes((one, one))
    overlap = one.__class__("other", Table.COIL, 0, Access.READ_ONLY, Kind.BOOL, "overlap")
    with pytest.raises(ValueError, match="overlap"):
        _indexes((one, overlap))
