import time

class errors(object):
    class SensorNotReadyError(Exception):
        pass

class W1ThermSensor(object):
    def __init__(self):
        self.temperature = 0

    def get_temperature(self):
        time.sleep(1)
        self.temperature += 1
        return 28
