#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Mock Equipment sử dụng thư viện secsgem.
Chạy ở chế độ PASSIVE, lắng nghe tại 127.0.0.1:5001 để Host kết nối đến và thực hiện handshake S1F13/S1F14.
Mô phỏng gửi thông điệp sự kiện S6F11 (Event Report) và thông điệp lỗi S5F1 (Alarm Report Send).
"""

import sys
import time
import logging
import threading
import secsgem.gem
import secsgem.hsms
import secsgem.common

# Thiết lập cấu hình logging cơ bản cho thư viện secsgem
logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=logging.INFO,
    stream=sys.stdout
)

class CustomEquipment(secsgem.gem.GemEquipmentHandler):
    """
    Subclass của GemEquipmentHandler để mô phỏng một máy Wire Bonder thật.
    """
    def __init__(self, settings: secsgem.common.Settings):
        super().__init__(settings)
        # Đăng ký luồng gửi dữ liệu mô phỏng khi kết nối thành công (COMMUNICATING)
        self.communication_state.communicating.events.enter.register(self._start_simulation)
        self.total_units = 120

    def _start_simulation(self, _):
        print("\n" + "#"*60)
        print("[MOCK EQUIPMENT] Kết nối thành công! Bắt đầu gửi dữ liệu định kỳ...")
        print("#"*60)
        threading.Thread(target=self._run_simulation, daemon=True).start()

    def _run_simulation(self):
        try:
            # Chờ 2 giây sau khi handshake thành công
            time.sleep(2)

            # Kịch bản 1: Máy chuyển sang trạng thái EXECUTING và bắt đầu chạy sản phẩm mới
            self.total_units += 1
            print(f"\n[MOCK EQUIPMENT SIM] Gửi S6F11 - Trạng thái: EXECUTING | Sản lượng: {self.total_units}")
            s6f11_exec = self.stream_function(6, 11)({
                "DATAID": 1,
                "CEID": 101,  # EXECUTING Event
                "RPT": [{
                    "RPTID": 1001,
                    "V": ["EXECUTING", self.total_units]
                }]
            })
            self.send_stream_function(s6f11_exec)

            time.sleep(3)

            # Kịch bản 2: Máy phát sinh cảnh báo lỗi S5F1 (Ví dụ: Kẹt dây kim loại hoặc lực kẹp clamp tension lỗi)
            print(f"\n[MOCK EQUIPMENT SIM] Gửi S5F1 - Báo lỗi (Alarm Set) - ALID: 99")
            s5f1_set = self.stream_function(5, 1)({
                "ALCD": 0x81,  # Alarm Set (Bit 8 = 1, Personal Safety)
                "ALID": 99,
                "ALTX": "Wire bonder clamp tension error!"
            })
            self.send_stream_function(s5f1_set)

            time.sleep(4)

            # Kịch bản 3: Kỹ thuật viên xử lý xong lỗi, máy gửi thông báo xóa lỗi S5F1 (Alarm Clear)
            print(f"\n[MOCK EQUIPMENT SIM] Gửi S5F1 - Xóa lỗi (Alarm Clear) - ALID: 99")
            s5f1_clear = self.stream_function(5, 1)({
                "ALCD": 0x01,  # Alarm Clear (Bit 8 = 0, Personal Safety)
                "ALID": 99,
                "ALTX": "Wire bonder clamp tension resolved."
            })
            self.send_stream_function(s5f1_clear)

            time.sleep(3)

            # Kịch bản 4: Máy hoàn thành chu kỳ chạy và chuyển sang IDLE, đồng thời cập nhật tổng sản lượng
            self.total_units += 1
            print(f"\n[MOCK EQUIPMENT SIM] Gửi S6F11 - Trạng thái: IDLE | Sản lượng: {self.total_units}")
            s6f11_idle = self.stream_function(6, 11)({
                "DATAID": 2,
                "CEID": 100,  # IDLE Event
                "RPT": [{
                    "RPTID": 1001,
                    "V": ["IDLE", self.total_units]
                }]
            })
            self.send_stream_function(s6f11_idle)

            print("\n[MOCK EQUIPMENT SIM] Hoàn thành toàn bộ kịch bản mô phỏng truyền dữ liệu thành công!")

        except Exception as e:
            print(f"\n[MOCK EQUIPMENT ERROR] Lỗi trong tiến trình mô phỏng: {e}")


def main():
    print("[MOCK EQUIPMENT] Đang cấu hình thiết bị mô phỏng...")

    # Cấu hình PASSIVE để lắng nghe kết nối từ Host
    settings = secsgem.hsms.HsmsSettings(
        address="127.0.0.1",
        port=5001,
        connect_mode=secsgem.hsms.HsmsConnectMode.PASSIVE,
        device_type=secsgem.common.DeviceType.EQUIPMENT
    )

    # Khởi tạo Equipment Handler tùy biến
    equipment = CustomEquipment(settings)

    print("[MOCK EQUIPMENT] Khởi động và bắt đầu lắng nghe tại 127.0.0.1:5001...")
    equipment.enable()

    try:
        print("[MOCK EQUIPMENT] Đang chạy. Nhấn Ctrl+C để thoát.")
        # Đợi và giữ chương trình chạy
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[MOCK EQUIPMENT] Đang đóng thiết bị mô phỏng...")
    finally:
        equipment.disable()
        print("[MOCK EQUIPMENT] Đã tắt thiết bị mô phỏng.")

if __name__ == "__main__":
    main()
