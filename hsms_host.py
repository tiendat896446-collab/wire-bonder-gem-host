#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Chương trình HSMS Host sử dụng thư viện secsgem.
Kế nối đến máy Equipment tại IP và Port được chỉ định (mặc định: 169.254.50.22:5001),
gửi thông điệp S1F13 (Establish Communications Request) nhằm handshake và in kết quả S1F14 ra màn hình.
"""

import argparse
import logging
import sys
import time
import secsgem.gem
import secsgem.hsms
import secsgem.common

# Thiết lập cấu hình logging cơ bản cho thư viện secsgem
logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=logging.INFO,
    stream=sys.stdout
)

class CustomHsmsHost(secsgem.gem.GemHostHandler):
    """
    Subclass của GemHostHandler để tùy biến việc in các thông điệp SECS gửi/nhận
    ra màn hình một cách trực quan nhất.
    """
    def __init__(self, settings: secsgem.common.Settings):
        super().__init__(settings)
        # Đăng ký dummy handler cho S1F14 để tránh cảnh báo "unexpected function received s01f14"
        self.register_stream_function(1, 14, self._on_s01f14_dummy)
        print(f"[INFO] Khởi tạo HSMS Host kết nối đến {settings.address}:{settings.port}")

    def _on_s01f14_dummy(self, handler, message):
        """
        Dummy handler cho S1F14 để tránh warning của SecsHandler.
        """
        pass

    def send_stream_function(self, function, *args, **kwargs):
        """
        Ghi đè phương thức send_stream_function để in thông tin trước khi gửi đi.
        """
        print("\n" + "="*50)
        print(f"[GỬI] Gửi thông điệp S{function.stream}F{function.function} (Establish Communications Request)")
        print(f"Nội dung thông điệp:\n{function}")
        print("="*50)
        return super().send_stream_function(function, *args, **kwargs)

    def _on_message_received(self, data: dict):
        """
        Ghi đè _on_message_received để bắt và in thông điệp S1F14 khi nhận được.
        """
        message = data.get("message")
        if message:
            decoded = self.settings.streams_functions.decode(message)
            print("\n" + "="*50)
            print(f"[NHẬN] Nhận thông điệp S{message.header.stream}F{message.header.function}")
            if decoded:
                print(f"Chi tiết thông điệp:\n{decoded}")
            else:
                print(f"Nội dung thô (Raw Message):\n{message}")
            print("="*50)

            # Nếu nhận được S1F14 (phản hồi của S1F13)
            if message.header.stream == 1 and message.header.function == 14:
                print("\n[HANDSHAKE] Hoàn tất handshake thành công! Kết nối đã chuyển sang trạng thái COMMUNICATING.")

        # Gọi phương thức của lớp cha để cập nhật State Machine và xử lý bình thường
        super()._on_message_received(data)


def main():
    parser = argparse.ArgumentParser(description="HSMS Host kết nối tới Equipment và thực hiện handshake S1F13.")
    parser.add_argument("--ip", default="169.254.50.22", help="Địa chỉ IP của Equipment (Mặc định: 169.254.50.22)")
    parser.add_argument("--port", type=int, default=5001, help="Cổng Port của Equipment (Mặc định: 5001)")
    args = parser.parse_args()

    # Tạo thiết lập kết nối HSMS
    # connect_mode=ACTIVE nghĩa là Host đóng vai trò chủ động kết nối tới Equipment.
    # device_type=HOST xác định thiết bị này đóng vai trò Host.
    settings = secsgem.hsms.HsmsSettings(
        address=args.ip,
        port=args.port,
        connect_mode=secsgem.hsms.HsmsConnectMode.ACTIVE,
        device_type=secsgem.common.DeviceType.HOST
    )

    # Khởi tạo Host Handler
    host = CustomHsmsHost(settings)

    print(f"\n[CONNECT] Đang kích hoạt kết nối tới Equipment tại {args.ip}:{args.port}...")
    host.enable()

    try:
        # Chờ tối đa 30 giây để hoàn thành handshake
        timeout = 30
        print(f"[INFO] Đang chờ thiết lập giao tiếp (S1F13/S1F14 Handshake) trong tối đa {timeout} giây...")
        success = host.waitfor_communicating(timeout=timeout)

        if success:
            print("\n[SUCCESS] Thiết lập kết nối và handshake thành công!")
            # Duy trì kết nối thêm một lúc để quan sát
            time.sleep(2)
        else:
            print("\n[TIMEOUT] Không thể hoàn thành handshake trong thời gian chờ.")

    except KeyboardInterrupt:
        print("\n[INFO] Chương trình bị ngắt bởi người dùng.")
    finally:
        print("[INFO] Đang đóng kết nối...")
        host.disable()
        print("[INFO] Đã đóng kết nối. Kết thúc chương trình.")

if __name__ == "__main__":
    main()
