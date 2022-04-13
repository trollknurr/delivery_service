class CarBrokenError(Exception):
    """
    During delivery our car was broken, packages must be redelivered
    """


class IncorrectAddressError(Exception):
    """
    User give us incorrect address, we can't process package
    """
