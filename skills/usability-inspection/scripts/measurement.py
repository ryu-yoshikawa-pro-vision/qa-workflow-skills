"""Exact measurement helpers. Browser values are inputs; this module owns arithmetic only."""
from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any


class MeasurementError(ValueError):
    pass


def _d(value: Any) -> Decimal:
    if isinstance(value, bool) or not isinstance(value, (int, float, str, Decimal)):
        raise MeasurementError("numeric browser value required")
    try:
        result = Decimal(str(value))
    except InvalidOperation as exc:
        raise MeasurementError("invalid decimal value") from exc
    if not result.is_finite():
        raise MeasurementError("non-finite measurement")
    return result


def viewport_overflow(metrics: dict[str, Any]) -> dict[str, Any]:
    required = {"viewport_width_css_px", "viewport_height_css_px", "scroll_width_css_px", "scroll_height_css_px"}
    if set(metrics) != required:
        raise MeasurementError("viewport metrics schema mismatch")
    width_delta = max(Decimal(0), _d(metrics["scroll_width_css_px"]) - _d(metrics["viewport_width_css_px"]))
    height_delta = max(Decimal(0), _d(metrics["scroll_height_css_px"]) - _d(metrics["viewport_height_css_px"]))
    return {"horizontal_overflow_css_px": str(width_delta), "vertical_overflow_css_px": str(height_delta),
            "horizontal_overflow": width_delta > 0, "vertical_overflow": height_delta > 0}


def target_geometry(box: dict[str, Any]) -> dict[str, Any]:
    if set(box) != {"x_css_px", "y_css_px", "width_css_px", "height_css_px"}:
        raise MeasurementError("geometry schema mismatch")
    width, height = _d(box["width_css_px"]), _d(box["height_css_px"])
    if width < 0 or height < 0:
        raise MeasurementError("negative geometry")
    return {**box, "area_css_px2": str(width * height)}


def contrast_ratio(luminance_a: Any, luminance_b: Any) -> Decimal:
    first, second = _d(luminance_a), _d(luminance_b)
    if not (0 <= first <= 1 and 0 <= second <= 1):
        raise MeasurementError("relative luminance must be within [0, 1]")
    lighter, darker = max(first, second), min(first, second)
    return ((lighter + Decimal("0.05")) / (darker + Decimal("0.05"))).quantize(Decimal("0.01"))


def interaction_elapsed_ms(start_ms: Any, end_ms: Any, *, same_page_clock: bool,
                           start_event_observed: bool, end_predicate_observed: bool) -> dict[str, Any]:
    if not same_page_clock or not start_event_observed or not end_predicate_observed:
        return {"status": "measurement-unavailable", "elapsed_ms": None}
    elapsed = _d(end_ms) - _d(start_ms)
    if elapsed < 0:
        raise MeasurementError("end clock precedes start clock")
    return {"status": "measured", "elapsed_ms": str(elapsed)}


def threshold_result(value: Any, threshold: Any | None, *, authority_ref: str | None) -> str:
    if threshold is None:
        if authority_ref:
            raise MeasurementError("authority without threshold")
        return "threshold-not-defined"
    if not authority_ref:
        raise MeasurementError("threshold requires an Authority ref")
    return "within-threshold" if _d(value) <= _d(threshold) else "over-threshold"
