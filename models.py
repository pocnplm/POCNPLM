# [POL-101] 센서 데이터 모델 정의
# Polarion Link: 요구사항 ID를 주석으로 달아두면 연동 시 시연하기 좋습니다.

class SensorData:
    def __init__(self, sensor_id: str, temperature: float, pressure: float):
        self.sensor_id = sensor_id
        self.temperature = temperature
        self.pressure = pressure

    def __repr__(self):
        return f"Sensor(ID: {self.sensor_id}, Temp: {self.temperature}°C, Pressure: {self.pressure}bar)"