# [POL-102] 센서 데이터 처리 및 임계값 검증 로직 구현

class SensorProcessor:
    def __init__(self, temp_limit: float = 100.0):
        self.temp_limit = temp_limit

    def analyze_data(self, data):
        """센서 데이터를 분석하여 경고 여부를 반환합니다."""
        if data.temperature > self.temp_limit:
            return "WARNING: High Temperature Detected"
        if data.pressure < 0:
            return "ERROR: Invalid Pressure Value"
        return "STATUS: Normal"

    def get_summary(self, data_list):
        """데이터 리스트의 평균 온도를 계산합니다."""
        if not data_list:
            return 0.0
        avg_temp = sum(d.temperature for d in data_list) / len(data_list)
        return round(avg_temp, 2)