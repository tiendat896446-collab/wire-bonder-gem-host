#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Chương trình HSMS Host sử dụng thư viện secsgem.
Kết nối đến máy Equipment tại IP và Port được chỉ định (mặc định: 169.254.50.22:5001),
gửi thông điệp S1F13 (Establish Communications Request) nhằm handshake,
đồng thời xử lý các thông điệp S6F11 (Event Report) và S5F1 (Alarm Report Send) từ máy gửi về.
Trích xuất sản lượng (Total Units) và trạng thái máy (IDLE, EXECUTING, ALARM),
sau đó lưu toàn bộ vào một cơ sở dữ liệu SQLite đơn giản.
"""

import argparse
import logging
import sys
import time
import sqlite3
import datetime
import secsgem.gem
import secsgem.hsms
import secsgem.common

# Thiết lập cấu hình logging cơ bản cho thư viện secsgem
logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=logging.INFO,
    stream=sys.stdout
)

class TelemetryDatabase:
    """
    Lớp quản lý cơ sở dữ liệu SQLite lưu trữ dữ liệu sản lượng và lỗi từ máy Wire Bonder.
    """
    def __init__(self, db_path="wire_bonder_data.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS equipment_telemetry (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    ceid INTEGER,
                    alid INTEGER,
                    altx TEXT,
                    machine_status TEXT NOT NULL,
                    total_units INTEGER NOT NULL
                );
            """)
            conn.commit()

    def log_telemetry(self, event_type, ceid=None, alid=None, altx=None, machine_status="IDLE", total_units=0):
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO equipment_telemetry (timestamp, event_type, ceid, alid, altx, machine_status, total_units)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (timestamp, event_type, ceid, alid, altx, machine_status, total_units))
            conn.commit()
            print(f"[SQLite] Đã lưu vào DB: {timestamp} | Loai: {event_type} | Trạng thái: {machine_status} | Sản lượng: {total_units}")


class CustomHsmsHost(secsgem.gem.GemHostHandler):
    """
    Subclass của GemHostHandler để tùy biến việc in các thông điệp SECS gửi/nhận
    và xử lý trích xuất dữ liệu S6F11 / S5F1 lưu vào SQLite.
    """
    def __init__(self, settings: secsgem.common.Settings):
        super().__init__(settings)
        # Khởi tạo DB SQLite
        self.db = TelemetryDatabase()

        # Đăng ký dummy handler cho S1F14 để tránh cảnh báo "unexpected function received s01f14"
        self.register_stream_function(1, 14, self._on_s01f14_dummy)

        # Lưu trữ trạng thái in-memory để dùng làm giá trị dự phòng (fallback)
        self.last_status = "IDLE"
        self.last_total_units = 0

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
        print(f"[GỬI] Gửi thông điệp S{function.stream}F{function.function}")
        print(f"Nội dung thông điệp:\n{function}")
        print("="*50)
        return super().send_stream_function(function, *args, **kwargs)

    def _on_message_received(self, data: dict):
        """
        Ghi đè _on_message_received để bắt và in thông điệp S1F14 khi nhận được.
        """
        message = data.get("message")
        if message:
            # Chỉ in thông tin S1F14 ở đây vì S6F11 và S5F1 sẽ được xử lý riêng bởi các callback chuyên dụng
            if message.header.stream == 1 and message.header.function == 14:
                decoded = self.settings.streams_functions.decode(message)
                print("\n" + "="*50)
                print(f"[NHẬN] Nhận thông điệp S1F14")
                if decoded:
                    print(f"Chi tiết thông điệp:\n{decoded}")
                else:
                    print(f"Nội dung thô (Raw Message):\n{message}")
                print("="*50)
                print("\n[HANDSHAKE] Hoàn tất handshake thành công! Kết nối đã chuyển sang trạng thái COMMUNICATING.")

        # Gọi phương thức của lớp cha để cập nhật State Machine và xử lý bình thường
        super()._on_message_received(data)

    def _on_s05f01(self, handler, message):
        """
        Ghi đè phương thức xử lý thông điệp S5F1 (Alarm Report Send) từ Equipment.
        """
        s5f1 = self.settings.streams_functions.decode(message)
        alid = int(s5f1.ALID.get())
        altx = str(s5f1.ALTX.get())
        alcd = int(s5f1.ALCD.get()[0]) if isinstance(s5f1.ALCD.get(), (bytes, list)) else int(s5f1.ALCD.get())

        # Trong tiêu chuẩn GEM, bit 8 của ALCD chỉ định Alarm Set (1) hay Alarm Clear (0)
        is_alarm_set = bool(alcd & 0x80)

        if is_alarm_set:
            self.last_status = "ALARM"
        else:
            self.last_status = "IDLE"  # Hoặc EXECUTING nếu đang chạy, tạm thời mặc định về IDLE

        print("\n" + "="*50)
        print(f"[NHẬN ALARM] S5F1 - Báo lỗi từ thiết bị")
        print(f"  - Alarm ID (ALID): {alid}")
        print(f"  - Alarm Text (ALTX): {altx}")
        print(f"  - Alarm Code (ALCD): {hex(alcd)} (Set={is_alarm_set})")
        print("="*50)

        # Lưu dữ liệu vào cơ sở dữ liệu SQLite
        self.db.log_telemetry(
            event_type="S5F1",
            alid=alid,
            altx=altx,
            machine_status=self.last_status,
            total_units=self.last_total_units
        )

        # Phản hồi lại S5F2 (Alarm Acknowledge)
        return self.stream_function(5, 2)(0)

    def _on_s06f11(self, handler, message):
        """
        Ghi đè phương thức xử lý thông điệp S6F11 (Event Report Send) từ Equipment.
        """
        s6f11 = self.settings.streams_functions.decode(message)
        ceid = int(s6f11.CEID.get())

        print("\n" + "="*50)
        print(f"[NHẬN EVENT] S6F11 - Báo cáo sự kiện")
        print(f"  - Event ID (CEID): {ceid}")
        print("="*50)

        total_units = None
        machine_status = None

        # Trích xuất đệ quy các thông số sản lượng và trạng thái máy từ cấu trúc dữ liệu của báo cáo
        def find_telemetry(data):
            nonlocal total_units, machine_status
            if isinstance(data, (str, bytes)):
                v_str = str(data).upper().strip()
                if v_str in ["IDLE", "EXECUTING", "ALARM"]:
                    machine_status = v_str
            elif isinstance(data, int) and not isinstance(data, bool):
                total_units = data
            elif isinstance(data, dict):
                for k, v in data.items():
                    check_match(k, v)
                    find_telemetry(v)
            elif isinstance(data, (list, tuple)):
                if len(data) == 2 and isinstance(data[0], (str, bytes)):
                    check_match(data[0], data[1])
                for item in data:
                    find_telemetry(item)
            elif hasattr(data, "get"):
                try:
                    find_telemetry(data.get())
                except Exception:
                    pass

        def check_match(key, val):
            nonlocal total_units, machine_status
            k_str = str(key).lower().strip()
            # Tìm tổng sản lượng (Total Units)
            if any(term in k_str for term in ["total unit", "total_unit", "units", "productcount", "totalunit", "san_luong"]):
                try:
                    total_units = int(val)
                except (ValueError, TypeError):
                    pass
            # Tìm trạng thái máy (IDLE, EXECUTING, ALARM)
            if any(term in k_str for term in ["status", "state", "trang_thai"]):
                v_str = str(val).upper().strip()
                if "IDLE" in v_str:
                    machine_status = "IDLE"
                elif "EXEC" in v_str or "RUN" in v_str:
                    machine_status = "EXECUTING"
                elif "ALARM" in v_str:
                    machine_status = "ALARM"

        find_telemetry(s6f11.get())

        # Áp dụng quy tắc dự phòng (Fallback Rules) nếu thông tin trạng thái không có trong các biến
        if ceid == 100:
            machine_status = "IDLE"
        elif ceid == 101:
            machine_status = "EXECUTING"
        elif ceid == 102:
            machine_status = "ALARM"

        # Cập nhật trạng thái in-memory
        if machine_status:
            self.last_status = machine_status
        if total_units is not None:
            self.last_total_units = total_units

        print(f"  -> Trạng thái trích xuất: {self.last_status}")
        print(f"  -> Sản lượng trích xuất: {self.last_total_units}")

        # Lưu dữ liệu vào cơ sở dữ liệu SQLite
        self.db.log_telemetry(
            event_type="S6F11",
            ceid=ceid,
            machine_status=self.last_status,
            total_units=self.last_total_units
        )

        # Phản hồi lại S6F12 (Event Acknowledge)
        return self.stream_function(6, 12)(0)


def print_db_records():
    """
    Hàm tiện ích để in toàn bộ dữ liệu hiện có trong SQLite ra màn hình nhằm kiểm chứng.
    """
    print("\n" + "="*80)
    print("DỮ LIỆU ĐÃ LƯU TRONG CƠ SỞ DỮ LIỆU SQLITE (wire_bonder_data.db):")
    print("="*80)
    try:
        with sqlite3.connect("wire_bonder_data.db") as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, timestamp, event_type, ceid, alid, altx, machine_status, total_units
                FROM equipment_telemetry
            """)
            rows = cursor.fetchall()
            for r in rows:
                print(f"ID: {r[0]} | Time: {r[1]} | Type: {r[2]} | CEID: {r[3]} | ALID: {r[4]} | ALTX: {r[5]} | Status: {r[6]} | Units: {r[7]}")
    except Exception as e:
        print(f"Lỗi đọc DB: {e}")
    print("="*80)


def main():
    parser = argparse.ArgumentParser(description="HSMS Host kết nối tới Equipment, handshake S1F13, và lưu S6F11/S5F1 vào SQLite.")
    parser.add_argument("--ip", default="169.254.50.22", help="Địa chỉ IP của Equipment (Mặc định: 169.254.50.22)")
    parser.add_argument("--port", type=int, default=5001, help="Cổng Port của Equipment (Mặc định: 5001)")
    parser.add_argument("--show-db", action="store_true", help="Chỉ hiển thị các dòng hiện tại trong SQLite DB rồi thoát")
    args = parser.parse_args()

    if args.show_db:
        print_db_records()
        sys.exit(0)

    # Tạo thiết lập kết nối HSMS
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
        # Tăng thời gian chờ lên 45 giây để kịp nhận các thông điệp định kỳ từ thiết bị mô phỏng
        timeout = 45
        print(f"[INFO] Đang chờ thiết lập giao tiếp và nhận dữ liệu telemetry trong tối đa {timeout} giây...")
        success = host.waitfor_communicating(timeout=timeout)

        if success:
            print("\n[SUCCESS] Thiết lập kết nối và handshake thành công!")
            print("[INFO] Host đang hoạt động, sẵn sàng nhận Event S6F11 và Alarm S5F1...")
            # Chờ thêm 15 giây để nhận các gói telemetry định kỳ gửi từ thiết bị
            time.sleep(15)
        else:
            print("\n[TIMEOUT] Không thể hoàn thành handshake trong thời gian chờ.")

    except KeyboardInterrupt:
        print("\n[INFO] Chương trình bị ngắt bởi người dùng.")
    finally:
        print("[INFO] Đang đóng kết nối...")
        host.disable()
        print("[INFO] Đã đóng kết nối.")

        # In các bản ghi đã lưu trong DB để chứng minh kết quả hoạt động
        print_db_records()
        print("[INFO] Kết thúc chương trình.")

if __name__ == "__main__":
    main()
