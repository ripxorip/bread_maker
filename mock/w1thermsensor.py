class errors(object):
    class SensorNotReadyError(Exception):
        pass

class W1ThermSensor(object):
    def __init__(self):
        pass

    def get_temperature(self):
        return 0
