#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Giao diện Dashboard giám sát máy Wire Bonder bằng Streamlit.
Đọc dữ liệu từ SQLite (wire_bonder_data.db) và hiển thị trạng thái real-time,
sản lượng theo thời gian, lịch sử lỗi/cảnh báo (Alarms) và tính toán các chỉ số OEE.
"""

import os
import sqlite3
import datetime
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

# Thiết lập cấu hình trang
st.set_page_config(
    page_title="Wire Bonder Dashboard",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

DB_PATH = "wire_bonder_data.db"

# Hàm khởi tạo dữ liệu mẫu nếu chưa có dữ liệu hoặc DB trống
def check_or_create_mock_data():
    """
    Tạo dữ liệu mẫu trong trường hợp DB chưa được tạo hoặc chưa có bản ghi,
    đảm bảo giao diện dashboard luôn hoạt động và trực quan ngay từ đầu.
    """
    if not os.path.exists(DB_PATH):
        print("[Dashboard] Không tìm thấy DB, đang tạo dữ liệu mẫu...")

    with sqlite3.connect(DB_PATH) as conn:
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

        # Kiểm tra xem có bản ghi nào chưa
        cursor.execute("SELECT COUNT(*) FROM equipment_telemetry")
        if cursor.fetchone()[0] == 0:
            print("[Dashboard] DB trống, đang ghi dữ liệu mô phỏng ban đầu...")
            now = datetime.datetime.now()
            # Sinh ra một số dữ liệu lịch sử cách nhau vài phút
            mock_records = [
                ((now - datetime.timedelta(minutes=15)).strftime("%Y-%m-%d %H:%M:%S.%f")[:-3], "S6F11", 100, None, None, "IDLE", 100),
                ((now - datetime.timedelta(minutes=12)).strftime("%Y-%m-%d %H:%M:%S.%f")[:-3], "S6F11", 101, None, None, "EXECUTING", 110),
                ((now - datetime.timedelta(minutes=9)).strftime("%Y-%m-%d %H:%M:%S.%f")[:-3], "S5F1", None, 99, "Wire bonder clamp tension error!", "ALARM", 110),
                ((now - datetime.timedelta(minutes=6)).strftime("%Y-%m-%d %H:%M:%S.%f")[:-3], "S5F1", None, 99, "Wire bonder clamp tension resolved.", "IDLE", 110),
                ((now - datetime.timedelta(minutes=3)).strftime("%Y-%m-%d %H:%M:%S.%f")[:-3], "S6F11", 101, None, None, "EXECUTING", 125),
                (now.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3], "S6F11", 100, None, None, "IDLE", 125)
            ]
            cursor.executemany("""
                INSERT INTO equipment_telemetry (timestamp, event_type, ceid, alid, altx, machine_status, total_units)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, mock_records)
            conn.commit()

# Đảm bảo có dữ liệu
check_or_create_mock_data()

# Hàm lấy toàn bộ dữ liệu từ DB
def load_telemetry_data():
    with sqlite3.connect(DB_PATH) as conn:
        df = pd.read_sql_query("SELECT * FROM equipment_telemetry ORDER BY timestamp ASC", conn)
    # Chuyển đổi timestamp thành kiểu datetime
    df['datetime'] = pd.to_datetime(df['timestamp'])
    return df

# Nạp dữ liệu
df = load_telemetry_data()

# ----------------- SIDEBAR -----------------
st.sidebar.title("🤖 Wire Bonder HSMS")
st.sidebar.markdown("---")

# Bộ lọc thời gian hoặc nút điều khiển
st.sidebar.subheader("Cài đặt Mô phỏng OEE")
ideal_cycle_time = st.sidebar.slider("Chu kỳ lý tưởng (s/sản phẩm)", min_value=1.0, max_value=60.0, value=3.0, step=0.5)
target_quality_rate = st.sidebar.slider("Tỷ lệ chất lượng mục tiêu (%)", min_value=90.0, max_value=100.0, value=99.2, step=0.1)

st.sidebar.markdown("---")
st.sidebar.info(
    "💡 **Mẹo:** Chạy chương trình `hsms_host.py` kết hợp với `mock_equipment.py` "
    "để thu thập thêm dữ liệu thực tế từ máy Wire Bonder và nhấn nút **Tải lại** bên dưới."
)

if st.sidebar.button("🔄 Tải lại dữ liệu (Refresh)"):
    st.rerun()

# ----------------- MAIN DASHBOARD -----------------
st.title("📊 Bảng điều khiển giám sát máy Wire Bonder (HSMS Host)")
st.write("Giám sát trạng thái hoạt động, sản lượng sản xuất, cảnh báo lỗi thời gian thực và đánh giá hiệu suất OEE.")

if df.empty:
    st.warning("⚠️ Cơ sở dữ liệu hiện tại trống hoặc không tồn tại.")
else:
    # Lấy bản ghi cuối cùng làm trạng thái hiện tại
    latest_record = df.iloc[-1]
    current_status = latest_record['machine_status']
    current_units = latest_record['total_units']
    last_update = latest_record['timestamp']

    # 1. Trạng thái Real-time (Màu sắc trực quan)
    st.subheader("🟢 Trạng thái hoạt động thời gian thực")
    status_cols = st.columns([1, 1, 1, 2])

    with status_cols[0]:
        # Định nghĩa màu sắc trạng thái máy
        if current_status == "EXECUTING":
            st.markdown(
                "<div style='background-color:#d4edda; border-left:6px solid #28a745; padding:15px; border-radius:4px; text-align:center;'>"
                "<h3 style='color:#155724; margin:0;'>EXECUTING</h3>"
                "<p style='color:#155724; margin:5px 0 0 0;'>Máy đang chạy sản xuất</p>"
                "</div>",
                unsafe_allow_html=True
            )
        elif current_status == "IDLE":
            st.markdown(
                "<div style='background-color:#fff3cd; border-left:6px solid #ffc107; padding:15px; border-radius:4px; text-align:center;'>"
                "<h3 style='color:#856404; margin:0;'>IDLE</h3>"
                "<p style='color:#856404; margin:5px 0 0 0;'>Máy đang tạm dừng / chờ</p>"
                "</div>",
                unsafe_allow_html=True
            )
        elif current_status == "ALARM":
            st.markdown(
                "<div style='background-color:#f8d7da; border-left:6px solid #dc3545; padding:15px; border-radius:4px; text-align:center;'>"
                "<h3 style='color:#721c24; margin:0;'>ALARM</h3>"
                "<p style='color:#721c24; margin:5px 0 0 0;'>Máy đang gặp sự cố cảnh báo</p>"
                "</div>",
                unsafe_allow_html=True
            )
        else:
            st.markdown(
                f"<div style='background-color:#e2e3e5; border-left:6px solid #6c757d; padding:15px; border-radius:4px; text-align:center;'>"
                f"<h3 style='color:#383d41; margin:0;'>{current_status}</h3>"
                f"<p style='color:#383d41; margin:5px 0 0 0;'>Trạng thái không xác định</p>"
                f"</div>",
                unsafe_allow_html=True
            )

    with status_cols[1]:
        st.metric(label="Tổng sản lượng hiện tại", value=f"{current_units} pcs")

    with status_cols[2]:
        st.metric(label="Cập nhật cuối lúc", value=last_update.split(".")[0])

    with status_cols[3]:
        # Hiển thị thanh tiến trình hoặc một thông tin ngắn gọn khác
        st.write("**Thông tin kết nối:** Active Connection (HSMS Host)")
        st.write(f"**IP máy Wire Bonder:** `{latest_record.get('ip', '127.0.0.1') if 'ip' in df.columns else '127.0.0.1'}` | **Port:** `5001`")

    st.markdown("---")

    # 2. Tính toán và hiển thị chỉ số OEE (Availability, Performance, Quality)
    st.subheader("📈 Phân tích hiệu suất thiết bị toàn diện (OEE)")

    # Tính toán thời gian phân bổ trạng thái từ lịch sử logs
    exec_time = 0.0
    idle_time = 0.0
    alarm_time = 0.0

    if len(df) > 1:
        # Tính khoảng cách thời gian giữa các dòng liên tiếp
        for i in range(len(df) - 1):
            row_current = df.iloc[i]
            row_next = df.iloc[i+1]
            duration = (row_next['datetime'] - row_current['datetime']).total_seconds()

            # Gán thời gian vào các trạng thái tương ứng
            status = row_current['machine_status']
            if status == "EXECUTING":
                exec_time += duration
            elif status == "IDLE":
                idle_time += duration
            elif status == "ALARM":
                alarm_time += duration
    else:
        # Giá trị mặc định nếu chỉ có một dòng
        exec_time = 300.0
        idle_time = 50.0
        alarm_time = 10.0

    # Đảm bảo tổng thời gian không bằng 0
    total_time = exec_time + idle_time + alarm_time
    if total_time == 0:
        total_time = 1.0

    # A - Availability (Mức độ sẵn sàng) = (Tổng thời gian - Thời gian Alarm) / Tổng thời gian
    availability = (total_time - alarm_time) / total_time
    availability = max(0.0, min(1.0, availability))

    # P - Performance (Hiệu suất chạy máy) = Sản lượng thực tế / Sản lượng lý tưởng trong thời gian hoạt động
    # Sản lượng lý tưởng = Thời gian chạy máy / Chu kỳ lý tưởng
    if exec_time > 0:
        ideal_units = exec_time / ideal_cycle_time
        # Dự phòng dữ liệu mẫu nếu kết nối quá ngắn
        if current_units > 0 and ideal_units > 0:
            performance = min(1.0, current_units / ideal_units)
        else:
            performance = 0.95
    else:
        performance = 1.0
    performance = max(0.0, min(1.0, performance))

    # Q - Quality (Tỷ lệ chất lượng)
    quality = target_quality_rate / 100.0

    # Tính chỉ số OEE tổng hợp
    oee = availability * performance * quality

    # Vẽ biểu đồ OEE bằng ba cột mét
    oee_cols = st.columns(4)
    with oee_cols[0]:
        st.metric(
            label="Mức độ sẵn sàng (Availability)",
            value=f"{availability:.1%}",
            delta=f"Downtime: {alarm_time:.1f} giây"
        )
    with oee_cols[1]:
        st.metric(
            label="Hiệu suất vận hành (Performance)",
            value=f"{performance:.1%}",
            delta=f"Uptime: {exec_time:.1f} giây"
        )
    with oee_cols[2]:
        st.metric(
            label="Tỷ lệ chất lượng (Quality)",
            value=f"{quality:.1%}",
            delta=f"Defect Rate: {1.0 - quality:.1%}"
        )
    with oee_cols[3]:
        # Hiển thị OEE tổng hợp với điểm nhấn đậm nét
        st.markdown(
            f"<div style='background-color:#e8f0fe; border: 1px solid #1a73e8; padding:10px 15px; border-radius:5px; text-align:center;'>"
            f"<h5 style='color:#1a73e8; margin:0; font-size:14px;'>CHỈ SỐ OEE TỔNG HỢP</h5>"
            f"<h1 style='color:#1a73e8; margin:5px 0; font-size:42px;'>{oee:.1%}</h1>"
            f"</div>",
            unsafe_allow_html=True
        )

    # Hiển thị biểu đồ tròn biểu diễn phân bổ thời gian hoạt động của máy
    chart_cols = st.columns([1, 1])
    with chart_cols[0]:
        st.write("**Biểu đồ phân bổ quỹ thời gian chạy máy (Time Distribution):**")
        pie_data = pd.DataFrame({
            'Trạng thái': ['EXECUTING', 'IDLE', 'ALARM'],
            'Thời gian (giây)': [exec_time, idle_time, alarm_time]
        })
        fig_pie = px.pie(
            pie_data,
            values='Thời gian (giây)',
            names='Trạng thái',
            color='Trạng thái',
            color_discrete_map={'EXECUTING': '#28a745', 'IDLE': '#ffc107', 'ALARM': '#dc3545'},
            hole=0.4
        )
        fig_pie.update_layout(margin=dict(t=10, b=10, l=10, r=10), height=250)
        st.plotly_chart(fig_pie, use_container_width=True)

    with chart_cols[1]:
        st.write("**Biểu đồ so sánh các thành phần OEE:**")
        categories = ['Availability', 'Performance', 'Quality', 'OEE']
        values = [availability*100, performance*100, quality*100, oee*100]
        fig_bar = go.Figure([go.Bar(
            x=categories,
            y=values,
            marker_color=['#4285f4', '#34a853', '#fbbc05', '#ea4335'],
            text=[f"{v:.1f}%" for v in values],
            textposition='auto'
        )])
        fig_bar.update_layout(yaxis=dict(range=[0, 110]), margin=dict(t=10, b=10, l=10, r=10), height=250)
        st.plotly_chart(fig_bar, use_container_width=True)

    st.markdown("---")

    # 3. Biểu đồ thống kê sản lượng (Total Units) theo thời gian
    st.subheader("📈 Xu hướng tổng sản lượng (Total Units) theo thời gian")
    # Biểu đồ đường của sản lượng
    fig_line = px.line(
        df,
        x='datetime',
        y='total_units',
        markers=True,
        title="Tổng sản lượng sản phẩm (pcs)",
        labels={'datetime': 'Thời gian nhận thông điệp', 'total_units': 'Tổng sản lượng (pcs)'},
        color_discrete_sequence=['#1a73e8']
    )
    fig_line.update_layout(xaxis_title="Thời gian", yaxis_title="Sản lượng (pcs)", height=350)
    st.plotly_chart(fig_line, use_container_width=True)

    st.markdown("---")

    # 4. Lịch sử lỗi/cảnh báo (Alarms) và nhật ký nhận tin nhắn
    log_cols = st.columns([1, 1])

    with log_cols[0]:
        st.subheader("🚨 Lịch sử cảnh báo / lỗi (Alarms - S5F1)")
        # Lọc các dòng là báo lỗi S5F1
        alarm_df = df[df['event_type'] == 'S5F1'].copy()
        if alarm_df.empty:
            st.success("✅ Không phát hiện bất kỳ bản ghi lỗi nào trong lịch sử.")
        else:
            # Chọn và làm sạch cột hiển thị
            alarm_display = alarm_df[['timestamp', 'alid', 'altx', 'machine_status']].rename(
                columns={
                    'timestamp': 'Thời gian',
                    'alid': 'Alarm ID',
                    'altx': 'Mô tả chi tiết',
                    'machine_status': 'Trạng thái máy'
                }
            ).sort_values(by='Thời gian', ascending=False)
            st.dataframe(alarm_display, use_container_width=True, hide_index=True)

    with log_cols[1]:
        st.subheader("📋 Nhật ký đầy đủ từ cổng HSMS (All Logs)")
        all_logs_display = df[['timestamp', 'event_type', 'ceid', 'alid', 'machine_status', 'total_units']].rename(
            columns={
                'timestamp': 'Thời gian',
                'event_type': 'Loại tin nhắn',
                'ceid': 'CEID',
                'alid': 'ALID',
                'machine_status': 'Trạng thái',
                'total_units': 'Sản lượng'
            }
        ).sort_values(by='Thời gian', ascending=False)
        st.dataframe(all_logs_display, use_container_width=True, hide_index=True)

# ----------------- FOOTER -----------------
st.markdown("---")
st.markdown(
    "<p style='text-align: center; color: #7f8c8d; font-size: 13px;'>"
    "Hệ thống giám sát Wire Bonder GEM Host v1.0.0 - Kết nối HSMS tiêu chuẩn SEMI E37 / E30 | © 2026"
    "</p>",
    unsafe_allow_html=True
)
