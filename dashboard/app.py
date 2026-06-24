"""
Streamlit Dashboard - Quản lý TikTok Affiliate Automation
"""
import streamlit as st
import requests
import pandas as pd
from datetime import datetime

API_URL = "http://localhost:8000"

st.set_page_config(
    page_title="TikTok Affiliate Dashboard",
    page_icon="🎵",
    layout="wide"
)

st.title("🎵 TikTok Affiliate Automation Dashboard")

# Sidebar navigation
page = st.sidebar.selectbox(
    "Navigation",
    ["📊 Overview", "🛍️ Products", "🎬 Videos", "📅 Schedule", "📈 Analytics"]
)

if page == "📊 Overview":
    col1, col2, col3, col4 = st.columns(4)

    # Placeholder metrics
    col1.metric("Total Products", "0", "Chưa sync")
    col2.metric("Videos Created", "0", "0 hôm nay")
    col3.metric("TikTok Views", "0", "0 tuần này")
    col4.metric("Affiliate Clicks", "0", "$0 revenue")

    st.divider()
    st.subheader("🔧 Quick Actions")

    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("🔄 Sync Shopee Products", type="primary"):
            st.info("Đang sync sản phẩm từ Shopee...")

    with col2:
        if st.button("🎬 Create Video Now", type="primary"):
            st.info("Đang tạo video...")

    with col3:
        if st.button("📤 Upload Pending Videos", type="primary"):
            st.info("Đang upload...")

    st.divider()
    st.subheader("📋 Recent Video Jobs")
    st.info("Chưa có jobs nào. Hãy bắt đầu bằng cách sync sản phẩm từ Shopee.")

elif page == "🛍️ Products":
    st.subheader("Danh sách sản phẩm")

    col1, col2 = st.columns([3, 1])
    with col2:
        if st.button("🔄 Sync từ Shopee"):
            st.success("Sync thành công!")

    st.dataframe(
        pd.DataFrame({
            "Tên sản phẩm": [],
            "Giá": [],
            "Danh mục": [],
            "Số video": [],
            "Trạng thái": []
        }),
        use_container_width=True
    )

elif page == "🎬 Videos":
    st.subheader("Video Jobs")

    status_filter = st.selectbox(
        "Lọc theo trạng thái",
        ["Tất cả", "Pending", "Rendering", "Rendered", "Published", "Failed"]
    )

    st.dataframe(
        pd.DataFrame({
            "ID": [], "Sản phẩm": [], "Trạng thái": [],
            "Tạo lúc": [], "Đăng lúc": [], "Views": []
        }),
        use_container_width=True
    )

elif page == "📈 Analytics":
    st.subheader("Performance Analytics")
    st.info("Kết nối TikTok API để xem analytics.")

    col1, col2 = st.columns(2)
    with col1:
        st.metric("Total Views (7 ngày)", "0")
        st.metric("Avg Engagement Rate", "0%")
    with col2:
        st.metric("Best Video", "N/A")
        st.metric("Affiliate Revenue", "$0")
