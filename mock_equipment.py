#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Mock Equipment sử dụng thư viện secsgem.
Chạy ở chế độ PASSIVE, lắng nghe tại 127.0.0.1:5001 để Host kết nối đến và thực hiện handshake S1F13/S1F14.
"""

import sys
import time
import logging
import secsgem.gem
import secsgem.hsms
import secsgem.common

# Thiết lập cấu hình logging cơ bản cho thư viện secsgem
logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=logging.INFO,
    stream=sys.stdout
)

def main():
    print("[MOCK EQUIPMENT] Đang cấu hình thiết bị mô phỏng...")

    # Cấu hình PASSIVE để lắng nghe kết nối từ Host
    settings = secsgem.hsms.HsmsSettings(
        address="127.0.0.1",
        port=5001,
        connect_mode=secsgem.hsms.HsmsConnectMode.PASSIVE,
        device_type=secsgem.common.DeviceType.EQUIPMENT
    )

    # Khởi tạo Equipment Handler
    equipment = secsgem.gem.GemEquipmentHandler(settings)

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
