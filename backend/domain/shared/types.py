"""Shared domain types used across multiple domains."""

from enum import Enum


class GroupByPeriod(str, Enum):
    """Period grouping options for aggregate queries."""

    DAY = "DAY"
    WEEK = "WEEK"
    MONTH = "MONTH"
