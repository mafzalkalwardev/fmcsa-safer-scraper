"""Errors raised while calling the official FMCSA QCMobile API."""

from __future__ import annotations


class FmcsaError(Exception):
    """Base error for FMCSA QCMobile lookups."""


class FmcsaAuthError(FmcsaError):
    """The FMCSA API rejected the WebKey."""


class FmcsaApiError(FmcsaError):
    """The FMCSA API could not complete the request."""
