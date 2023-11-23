"""Tests for dtcalc."""
from datetime import datetime, timedelta, timezone

import dtcalc

test_date_str = "2023-11-21T04:30:05Z"
test_date_dt = datetime(2023, 11, 21, 4, 30, 5, tzinfo=timezone.utc)

test_tzdate_str = "2023-11-21T04:30:05+07:00"
tz = timezone(timedelta(hours=7))
test_tzdate_dt = datetime(2023, 11, 21, 4, 30, 5, tzinfo=tz)


def test_literals():
    c = dtcalc.parse("4d")
    assert isinstance(c.root, dtcalc.DurationLiteral)
    assert c.evaluate() == timedelta(days=4)

    c = dtcalc.parse("0.5d")
    assert isinstance(c.root, dtcalc.DurationLiteral)
    assert c.evaluate() == timedelta(days=0.5)

    c = dtcalc.parse("0.8")
    assert isinstance(c.root, dtcalc.NumberLiteral)
    assert c.evaluate() == 0.8

    c = dtcalc.parse("0.8")
    assert isinstance(c.root, dtcalc.NumberLiteral)
    assert c.evaluate() == 0.8

    c = dtcalc.parse(test_date_str)
    assert isinstance(c.root, dtcalc.DatetimeLiteral)
    assert c.evaluate() == test_date_dt

    c = dtcalc.parse(test_tzdate_str)
    assert isinstance(c.root, dtcalc.DatetimeLiteral)
    assert c.evaluate() == test_tzdate_dt


def test_identifiers():
    c = dtcalc.parse("now")
    assert isinstance(c.root, dtcalc.Identifier)
    assert c.root.name == "now"
    assert "now" in c.identifiers
    assert c.root is c.identifiers["now"]

    c.identifiers["now"].set_value(test_date_dt)
    assert c.evaluate() == test_date_dt


def test_parse():
    c = dtcalc.parse("4 * 4d")
    assert isinstance(c.root, dtcalc.BinOp)
    assert c.root.op == "*"
    assert isinstance(c.root.lhs, dtcalc.NumberLiteral)
    assert isinstance(c.root.rhs, dtcalc.DurationLiteral)
    assert c.root.lhs.text == "4"
    assert c.root.rhs.text == "4d"

    assert c.evaluate() == timedelta(days=16)

    c = dtcalc.parse("   1990-10-05T12:40:30Z-400d  ")
    assert isinstance(c.root, dtcalc.BinOp)
    assert c.root.op == "-"
    assert isinstance(c.root.lhs, dtcalc.DatetimeLiteral)
    assert isinstance(c.root.rhs, dtcalc.DurationLiteral)
    assert c.root.lhs.text == "1990-10-05T12:40:30Z"
    assert c.root.rhs.text == "400d"

    assert c.evaluate() == datetime(
        1989,
        8,
        31,
        12,
        40,
        30,
        tzinfo=timezone.utc,
    )


def test_eval():
    c = dtcalc.parse("20 - 6 - 4")
    assert c.evaluate() == 10.0

    c = dtcalc.parse("5 * (16 - 4) / 3 * 2d")
    assert c.evaluate() == timedelta(days=40)

    c = dtcalc.parse("5 * (16 - 4) / 3 * 2d + 10d -1d*(20 + 5 + 5*5)")
    assert c.evaluate() == timedelta(days=0)

    c = dtcalc.parse("now + 15d * 2")
    c.identifiers["now"].set_value(
        datetime(1990, 1, 10, 2, 3, 4, tzinfo=timezone(timedelta(hours=5))),
    )
    assert c.evaluate() == datetime(
        1990, 2, 9, 2, 3, 4, tzinfo=timezone(timedelta(hours=5)),
    )

    c = dtcalc.parse("now + 15d * 2")
    assert c.evaluate(
        now=datetime(1990, 1, 10, 2, 3, 4, tzinfo=timezone(timedelta(hours=5))),
    ) == datetime(1990, 2, 9, 2, 3, 4, tzinfo=timezone(timedelta(hours=5)))
