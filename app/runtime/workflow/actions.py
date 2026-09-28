class Action:
    def execute(self, context=None):
        raise NotImplementedError


class PrintAction(Action):
    def __init__(self, message: str):
        self.message = message

    def execute(self, context=None):
        print(self.message)

class SetVariableAction(Action):
    def __init__(
        self,
        key,
        value,
    ):
        self.key = key
        self.value = value

    def execute(
        self,
        context=None,
    ):
        context.set(
            self.key,
            self.value,
        )

class PrintVariableAction(Action):
    def __init__(
        self,
        key,
    ):
        self.key = key

    def execute(
        self,
        context=None,
    ):
        print(
            context.get(
                self.key
            )
        )