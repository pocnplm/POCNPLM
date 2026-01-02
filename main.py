from models import SensorData
from sensor_processor import SensorProcessor

def main():
    print("=== Automotive Sensor Monitoring System Starting... ===")
    
    # 더미 데이터 생성
    sensors = [
        SensorData("FRONT_01", 25.5, 2.2),
        SensorData("REAR_01", 105.2, 2.1), # 경고 발생 데이터
    ]
    
    processor = SensorProcessor()
    
    for sensor in sensors:
        status = processor.analyze_data(sensor)
        print(f"[{sensor.sensor_id}] Result: {status}")

if __name__ == "__main__":
    main()