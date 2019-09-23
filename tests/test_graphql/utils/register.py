"""Operations scenario register decorator."""


class RegisterOperationTestScenario(object):
    """
    Simple decorator class used to register scenarios for operations.

    Used to verify that there exists test for a set of scenarios on a set of
    operations.
    """

    def __init__(self):
        self._register = {}

    def add_scenario(self, operation_name, scenario):
        """Register a scenario for an operation"""
        def wrapper(func):
            if operation_name not in self._register:
                self._register[operation_name] = []

            self._register[operation_name].append(scenario)
            return func
        return wrapper

    def operations_test_exist_for_scenario(self, operation_name, scenario):
        """Check if a scenario is registered for an operations."""
        if (operation_name in self._register and
                scenario in self._register[operation_name]):
            return True
        return False
