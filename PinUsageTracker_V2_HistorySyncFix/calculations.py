from __future__ import annotations


def expected_pins(kettles_planned: float, pins_per_kettle: float) -> float:
    return round(
        max(float(kettles_planned), 0.0)
        * max(float(pins_per_kettle), 0.0),
        4,
    )


def new_expected_pins(expected: float, yield_percent: float) -> float:
    """
    Applies the actual yield to Expected Pins.

    Example:
    Expected Pins = 28.6575
    Yield = 95%
    New Expected = 27.224625
    """
    expected = max(float(expected), 0.0)
    yield_percent = min(max(float(yield_percent), 0.0), 100.0)

    return expected * (yield_percent / 100.0)


def pin_variance(actual_pins: float, new_expected: float) -> float:
    return float(actual_pins) - float(new_expected)


def format_number(value: float) -> float:
    return round(float(value), 2)
