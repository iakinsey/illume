"""Warnings."""


class SizeWarning(Warning):

    """Maximum size exceeded."""

    code = -1


class ErrorRateWarning(Warning):

    """Maximum error rate exceeded."""

    code = -2


class InvalidActorCount(Warning):

    """There are more actors in a pool than there should be."""

    code = -3
