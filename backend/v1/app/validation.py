"""
Reusable input validation.

Validators collect every problem in a request instead of stopping at the
first one, so the frontend can highlight all invalid fields at once.
"""

import re
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any, Iterable

from app.responses import ApiError

EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


# [FIELD VALIDATOR HERE]
# How: A Validator reads fields from the request body, records an error
#      message per bad field, and raise_if_errors() turns them into one 400
#      response with a "details" map like {"email": "Must be a valid email."}.
# Why: Reporting all errors together saves round trips while filling in forms,
#      and every endpoint validates the same way with the same messages.
class Validator:
    """Collects cleaned values and per-field errors from a request body."""

    def __init__(self, data: Any) -> None:
        """
        Start validating a request body.

        Args:
            data: The parsed JSON body.

        Raises:
            ApiError: 400 if the body is not a JSON object.
        """
        if not isinstance(data, dict):
            raise ApiError(400, "invalid_body", "Request body must be a JSON object.")
        self.data = data
        self.errors: dict[str, str] = {}
        self.cleaned: dict[str, Any] = {}

    def has(self, name: str) -> bool:
        """
        Check whether a field was sent.

        Args:
            name: Field name.

        Returns:
            True if the field is present in the body.
        """
        return name in self.data

    def string(self, name: str, required: bool = False, max_length: int = 255,
               allow_empty: bool = False) -> None:
        """
        Validate a text field and trim surrounding spaces.

        Args:
            name: Field name.
            required: Whether the field must be present.
            max_length: Maximum allowed length.
            allow_empty: Whether "" (or null) is accepted to clear the field.
        """
        if not self.has(name):
            if required:
                self.errors[name] = "This field is required."
            return
        value = self.data[name]
        if value is None and allow_empty and not required:
            self.cleaned[name] = None
            return
        if not isinstance(value, str):
            self.errors[name] = "Must be text."
            return
        value = value.strip()
        if not value and not allow_empty:
            self.errors[name] = "Cannot be empty."
        elif len(value) > max_length:
            self.errors[name] = f"Must be at most {max_length} characters."
        else:
            self.cleaned[name] = value or None

    def email(self, name: str, required: bool = False) -> None:
        """
        Validate an email address and store it in lowercase.

        Args:
            name: Field name.
            required: Whether the field must be present.
        """
        self.string(name, required=required, max_length=254)
        if name in self.cleaned:
            value = self.cleaned[name].lower()
            if not EMAIL_PATTERN.match(value):
                self.errors[name] = "Must be a valid email address."
                del self.cleaned[name]
            else:
                self.cleaned[name] = value

    def choice(self, name: str, options: Iterable[str], required: bool = False) -> None:
        """
        Validate that a field is one of a fixed set of values.

        Args:
            name: Field name.
            options: Allowed values.
            required: Whether the field must be present.
        """
        allowed = list(options)
        if not self.has(name):
            if required:
                self.errors[name] = "This field is required."
            return
        if self.data[name] not in allowed:
            self.errors[name] = f"Must be one of: {', '.join(allowed)}."
        else:
            self.cleaned[name] = self.data[name]

    def money(self, name: str, required: bool = False) -> None:
        """
        Validate a non-negative amount with at most two decimal places.

        Args:
            name: Field name.
            required: Whether the field must be present.
        """
        if not self.has(name):
            if required:
                self.errors[name] = "This field is required."
            return
        value = self.data[name]
        if value is None and not required:
            self.cleaned[name] = None
            return
        if isinstance(value, bool):
            self.errors[name] = "Must be a number."
            return
        try:
            amount = Decimal(str(value))
        except (InvalidOperation, ValueError):
            self.errors[name] = "Must be a number."
            return
        if not amount.is_finite() or amount < 0:
            self.errors[name] = "Must be zero or more."
        elif amount.as_tuple().exponent < -2:  # type: ignore[operator]
            self.errors[name] = "Must have at most two decimal places."
        else:
            self.cleaned[name] = amount

    # [DATE AND NUMBER VALIDATORS HERE]
    # How: Validators for dates (YYYY-MM-DD), whole numbers, hours, and lists
    #      of text, with the same error-collecting behavior as the others.
    # Why: Projects, milestones, and hour assignments all need these checks,
    #      and sharing them keeps error messages identical everywhere.
    def date(self, name: str, required: bool = False) -> None:
        """
        Validate a YYYY-MM-DD date. The cleaned value stays an ISO string.

        Args:
            name: Field name.
            required: Whether the field must be present.
        """
        if not self.has(name):
            if required:
                self.errors[name] = "This field is required."
            return
        parsed = parse_date(self.data[name])
        if parsed is None:
            self.errors[name] = "Must be a date in YYYY-MM-DD format."
        else:
            self.cleaned[name] = parsed.isoformat()

    def integer(self, name: str, required: bool = False,
                minimum: int = 0, maximum: int = 1_000_000) -> None:
        """
        Validate a whole number within a range.

        Args:
            name: Field name.
            required: Whether the field must be present.
            minimum: Smallest allowed value.
            maximum: Largest allowed value.
        """
        if not self.has(name):
            if required:
                self.errors[name] = "This field is required."
            return
        value = self.data[name]
        if isinstance(value, bool) or not isinstance(value, int):
            self.errors[name] = "Must be a whole number."
        elif not minimum <= value <= maximum:
            self.errors[name] = f"Must be between {minimum} and {maximum}."
        else:
            self.cleaned[name] = value

    def hours(self, name: str, required: bool = False) -> None:
        """
        Validate an hour amount: more than 0, at most 40, two decimals max.

        Args:
            name: Field name.
            required: Whether the field must be present.
        """
        if not self.has(name):
            if required:
                self.errors[name] = "This field is required."
            return
        value = self.data[name]
        if isinstance(value, bool) or not isinstance(value, (int, float, str)):
            self.errors[name] = "Must be a number."
            return
        try:
            amount = Decimal(str(value))
        except (InvalidOperation, ValueError):
            self.errors[name] = "Must be a number."
            return
        if not amount.is_finite() or amount <= 0 or amount > 40:
            self.errors[name] = "Must be more than 0 and at most 40."
        elif amount.as_tuple().exponent < -2:  # type: ignore[operator]
            self.errors[name] = "Must have at most two decimal places."
        else:
            self.cleaned[name] = amount

    def string_list(self, name: str, max_items: int = 50, max_length: int = 500) -> None:
        """
        Validate a list of text items, dropping blank ones.

        Args:
            name: Field name.
            max_items: Maximum number of items.
            max_length: Maximum length of each item.
        """
        if not self.has(name):
            return
        value = self.data[name]
        if value is None:
            self.cleaned[name] = []
            return
        if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
            self.errors[name] = "Must be a list of text items."
            return
        items = [v.strip() for v in value if v.strip()]
        if len(items) > max_items:
            self.errors[name] = f"Must have at most {max_items} items."
        elif any(len(v) > max_length for v in items):
            self.errors[name] = f"Each item must be at most {max_length} characters."
        else:
            self.cleaned[name] = items

    def raw(self, name: str) -> None:
        """
        Copy a field through without validation (validated elsewhere).

        Args:
            name: Field name.
        """
        if self.has(name):
            self.cleaned[name] = self.data[name]

    def raise_if_errors(self) -> None:
        """
        Raise a single 400 error listing every invalid field.

        Raises:
            ApiError: 400 with a details map, if any field failed.
        """
        if self.errors:
            raise ApiError(400, "validation_error", "Some fields are invalid.", self.errors)


def reject_unknown_fields(data: dict[str, Any], allowed: Iterable[str]) -> None:
    """
    Fail if the body contains fields the caller isn't allowed to set.

    Args:
        data: The parsed JSON body.
        allowed: Field names permitted for this caller.

    Raises:
        ApiError: 400 naming the fields that aren't allowed.
    """
    unknown = sorted(set(data) - set(allowed))
    if unknown:
        raise ApiError(400, "unknown_fields",
                       "These fields can't be set here: " + ", ".join(unknown) + ".",
                       {field: "Not allowed." for field in unknown})


def parse_date(value: Any) -> date | None:
    """
    Parse a "YYYY-MM-DD" string into a date.

    Args:
        value: The value to parse.

    Returns:
        The date, or None if the value isn't a valid date string.
    """
    if not isinstance(value, str):
        return None
    try:
        return date.fromisoformat(value.strip())
    except ValueError:
        return None
