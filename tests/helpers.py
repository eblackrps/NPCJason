class FakeLogger:
    def __init__(self):
        self.messages = {"info": [], "warning": [], "error": [], "exception": []}

    def info(self, message):
        self.messages["info"].append(str(message))

    def warning(self, message):
        self.messages["warning"].append(str(message))

    def error(self, message):
        self.messages["error"].append(str(message))

    def exception(self, message):
        self.messages["exception"].append(str(message))


class FakeRoot:
    def __init__(self):
        self._next_id = 1
        self.scheduled = {}

    def after(self, delay_ms, callback):
        after_id = f"after-{self._next_id}"
        self._next_id += 1
        self.scheduled[after_id] = {"delay_ms": delay_ms, "callback": callback}
        return after_id

    def after_cancel(self, after_id):
        self.scheduled.pop(after_id, None)

    def run_next(self):
        after_id, payload = next(iter(self.scheduled.items()))
        self.scheduled.pop(after_id, None)
        payload["callback"]()
        return payload["delay_ms"]


class MemoryStore:
    def __init__(self, payload):
        self.payload = payload

    def read(self):
        return self.payload

    def write(self, payload):
        self.payload = payload

    def update(self, mutator):
        return mutator(self.payload)
