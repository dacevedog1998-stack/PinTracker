from __future__ import annotations


def expected_pins(
    kettles_planned: float,
    pins_per_kettle: float,
) -> float:

    kettles_planned = max(
        float(kettles_planned),
        0.0,
    )

    pins_per_kettle = max(
        float(pins_per_kettle),
        0.0,
    )

    return round(
        kettles_planned * pins_per_kettle,
        4,
    )


def new_expected_pins(
    expected: float,
    yield_percent: float,
) -> float:
    """
    Calculate the yield-adjusted expected pins.

    Yield values greater than 100% are allowed.

    Example:
    Expected Pins = 28.68
    Yield = 105%

    New Expected = 30.11
    """

    expected = max(
        float(expected),
        0.0,
    )

    yield_percent = max(
        float(yield_percent),
        0.0,
    )

    return expected * (
        yield_percent / 100.0
    )


def pin_variance(
    actual_pins: float,
    new_expected: float,
) -> float:

    return (
        float(actual_pins)
        -
        float(new_expected)
    )


def format_number(
    value: float,
) -> float:

    return round(
        float(value),
        2,
    )
