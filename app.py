import streamlit as st
import pandas as pd
import chardet
import io
import json
from datetime import datetime
from fpdf import FPDF

st.set_page_config(
    page_title="CSV Cleaner Pro",
    page_icon="🧹",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ====================== SESSION STATE ======================
if "usage_count" not in st.session_state:
    st.session_state.usage_count = 0
if "is_unlocked" not in st.session_state:
    st.session_state.is_unlocked = False
if "history" not in st.session_state:
    st.session_state.history = []
if "last_cleaned_df" not in st.session_state:
    st.session_state.last_cleaned_df = None
if "last_logs" not in st.session_state:
    st.session_state.last_logs = []

FREE_LIMIT = 3
GUMROAD_LINK = "https://yourname.gumroad.com/l/csv-cleaner"  # <-- Thay link thật của bạn sau

# ====================== HEADER ======================
st.title("🧹 CSV Cleaner Pro")
st.caption("Smart cleaning • Presets • PDF Report • History • Compare files")

# ====================== PAYWALL CHECK ======================
def check_access():
    if st.session_state.is_unlocked:
        return True
    if st.session_state.usage_count < FREE_LIMIT:
        return True
    return False

# Sidebar - License
st.sidebar.header("🔑 License")
license_key = st.sidebar.text_input("Enter License Key (after purchase)", type="password")
if license_key.strip().lower() == "pro-2026":  # Key demo, bạn đổi sau
    st.session_state.is_unlocked = True
    st.sidebar.success("Unlocked - Full version")
elif st.session_state.is_unlocked:
    st.sidebar.success("Unlocked - Full version")
else:
    remaining = max(0, FREE_LIMIT - st.session_state.usage_count)
    st.sidebar.warning(f"Free trials left: {remaining}/{FREE_LIMIT}")
    st.sidebar.markdown(f"[➡️ Buy Full Version]({GUMROAD_LINK})")

# ====================== TABS ======================
tab1, tab2, tab3 = st.tabs(["🧹 Clean CSV", "📊 Compare 2 Files", "📜 History & Presets"])

# ====================== TAB 1: CLEAN ======================
with tab1:
    st.sidebar.header("⚙️ Cleaning Options")

    uploaded_file = st.sidebar.file_uploader("Upload CSV file", type=["csv", "txt"], key="clean_upload")

    if uploaded_file is None:
        st.info("👈 Upload a CSV file to start cleaning")
    else:
        # File size check
        file_size_mb = len(uploaded_file.getvalue()) / (1024 * 1024)
        if file_size_mb > 50:
            st.warning(f"File is large ({file_size_mb:.1f} MB). Processing may be slow.")

        raw_data = uploaded_file.getvalue()
        result = chardet.detect(raw_data)
        encoding = result["encoding"] if result["encoding"] else "utf-8"

        sample = raw_data[:2000].decode(encoding, errors="ignore")
        if sample.count(";") > sample.count(","):
            separator = ";"
        elif sample.count("\t") > sample.count(","):
            separator = "\t"
        else:
            separator = ","

        st.sidebar.success(f"Encoding: **{encoding}** | Separator: `{repr(separator)}`")

        try:
            df = pd.read_csv(io.BytesIO(raw_data), encoding=encoding, sep=separator)
        except Exception as e:
            st.error(f"Cannot read file: {e}")
            st.stop()

        original_rows, original_cols = len(df), len(df.columns)

        st.subheader("📊 Original Data")
        c1, c2, c3 = st.columns(3)
        c1.metric("Rows", original_rows)
        c2.metric("Columns", original_cols)
        c3.metric("Size", f"{file_size_mb:.2f} MB")

        preview_rows = st.sidebar.slider("Preview rows", 5, 30, 10)
        st.dataframe(df.head(preview_rows), use_container_width=True)

        # Presets
        st.sidebar.subheader("🚀 One-click Presets")
        preset = st.sidebar.radio(
            "Preset",
            ["None (Custom)", "Shopee / E-commerce", "Excel Ready", "Google Sheets", "Accounting"],
            index=0
        )

        # Default values
        remove_duplicates = True
        remove_empty_rows = True
        remove_empty_cols = True
        strip_whitespace = True
        normalize_columns = True
        fill_method = "Do not fill"
        fix_dates = False
        auto_fix = False

        if preset != "None (Custom)":
            remove_duplicates = remove_empty_rows = remove_empty_cols = strip_whitespace = True
            auto_fix = True
            fix_dates = True
            if preset == "Shopee / E-commerce":
                fill_method = "Fill with text (N/A)"
                normalize_columns = True
            elif preset == "Excel Ready":
                normalize_columns = False
                fill_method = "Do not fill"
            elif preset == "Google Sheets":
                normalize_columns = True
            elif preset == "Accounting":
                fill_method = "Fill with text (N/A)"
                normalize_columns = True

        st.sidebar.markdown("---")
        remove_duplicates = st.sidebar.checkbox("Remove duplicate rows", value=remove_duplicates)
        remove_empty_rows = st.sidebar.checkbox("Remove empty rows", value=remove_empty_rows)
        remove_empty_cols = st.sidebar.checkbox("Remove empty columns", value=remove_empty_cols)
        strip_whitespace = st.sidebar.checkbox("Strip whitespace", value=strip_whitespace)
        normalize_columns = st.sidebar.checkbox("Normalize column names", value=normalize_columns)
        auto_fix = st.sidebar.checkbox("Auto Fix Common Errors", value=auto_fix)

        fill_method = st.sidebar.selectbox(
            "Fill missing values",
            ["Do not fill", "Fill with text (N/A)", "Mean (average)", "Median"],
            index=["Do not fill", "Fill with text (N/A)", "Mean (average)", "Median"].index(fill_method)
        )

        fix_dates = st.sidebar.checkbox("Normalize date columns", value=fix_dates)
        date_columns = st.sidebar.multiselect("Date columns", df.columns.tolist()) if fix_dates else []

        # Clean button
        if st.button("🚀 Clean & Download", type="primary", use_container_width=True):
            if not check_access():
                st.error("Free trial limit reached. Please purchase the full version.")
                st.markdown(f"[➡️ Buy Full Version on Gumroad]({GUMROAD_LINK})")
                st.stop()

            cleaned_df = df.copy()
            logs = []

            if normalize_columns:
                cleaned_df.columns = (
                    cleaned_df.columns.str.strip().str.lower()
                    .str.replace(r"\s+", "_", regex=True)
                    .str.replace(r"[^\w_]", "", regex=True)
                )
                logs.append("Normalized column names")

            if strip_whitespace:
                for col in cleaned_df.select_dtypes(include="object").columns:
                    cleaned_df[col] = cleaned_df[col].astype(str).str.strip()
                    cleaned_df[col] = cleaned_df[col].replace(["None", "nan", "NaN", ""], pd.NA)
                logs.append("Stripped whitespace")

            if auto_fix:
                for col in cleaned_df.columns:
                    if cleaned_df[col].dtype == "object":
                        converted = pd.to_numeric(cleaned_df[col], errors="coerce")
                        if converted.notna().sum() > len(cleaned_df) * 0.6:
                            cleaned_df[col] = converted
                            logs.append(f"Auto-converted to numeric: {col}")
                        if "email" in col.lower():
                            cleaned_df[col] = cleaned_df[col].astype(str).str.lower().str.strip()
                logs.append("Applied Auto Fix")

            if remove_empty_rows:
                before = len(cleaned_df)
                cleaned_df = cleaned_df.dropna(how="all")
                logs.append(f"Removed {before - len(cleaned_df)} empty rows")

            if remove_empty_cols:
                before = cleaned_df.shape[1]
                cleaned_df = cleaned_df.dropna(axis=1, how="all")
                logs.append(f"Removed {before - cleaned_df.shape[1]} empty columns")

            if remove_duplicates:
                before = len(cleaned_df)
                cleaned_df = cleaned_df.drop_duplicates()
                logs.append(f"Removed {before - len(cleaned_df)} duplicates")

            if fill_method == "Fill with text (N/A)":
                cleaned_df = cleaned_df.fillna("N/A")
                logs.append("Filled with N/A")
            elif fill_method == "Mean (average)":
                num_cols = cleaned_df.select_dtypes(include="number").columns
                cleaned_df[num_cols] = cleaned_df[num_cols].fillna(cleaned_df[num_cols].mean())
                logs.append("Filled with mean")
            elif fill_method == "Median":
                num_cols = cleaned_df.select_dtypes(include="number").columns
                cleaned_df[num_cols] = cleaned_df[num_cols].fillna(cleaned_df[num_cols].median())
                logs.append("Filled with median")

            if fix_dates and date_columns:
                for col in date_columns:
                    target = col if col in cleaned_df.columns else col.strip().lower().replace(" ", "_")
                    if target in cleaned_df.columns:
                        try:
                            cleaned_df[target] = pd.to_datetime(
                                cleaned_df[target], errors="coerce", dayfirst=True, format="mixed"
                            ).dt.strftime("%Y-%m-%d")
                            cleaned_df[target] = cleaned_df[target].fillna("")
                            logs.append(f"Normalized dates: {target}")
                        except:
                            pass

            # Save to session
            st.session_state.usage_count += 1
            st.session_state.last_cleaned_df = cleaned_df
            st.session_state.last_logs = logs
            st.session_state.history.append({
                "time": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "rows_before": original_rows,
                "rows_after": len(cleaned_df),
                "preset": preset
            })

            st.success("Cleaning completed!")

            # Metrics
            st.subheader("📈 Before / After")
            m1, m2, m3 = st.columns(3)
            m1.metric("Rows", original_rows, delta=len(cleaned_df) - original_rows)
            m2.metric("Columns", original_cols, delta=cleaned_df.shape[1] - original_cols)
            m3.metric("Missing values left", int(cleaned_df.isna().sum().sum()))

            # Smart Report
            st.subheader("🧠 Smart Data Type Report")
            report_data = []
            for col in cleaned_df.columns:
                report_data.append({
                    "Column": col,
                    "Type": str(cleaned_df[col].dtype),
                    "Non-null": int(cleaned_df[col].notna().sum()),
                    "Sample": str(cleaned_df[col].dropna().head(2).tolist())[:60]
                })
            st.dataframe(pd.DataFrame(report_data), use_container_width=True)

            with st.expander("Actions performed"):
                for log in logs:
                    st.write("•", log)

            st.subheader("Preview")
            st.dataframe(cleaned_df.head(preview_rows), use_container_width=True)

            # Downloads
            st.subheader("📥 Download")
            col_dl1, col_dl2, col_dl3 = st.columns(3)

            with col_dl1:
                csv_buf = io.StringIO()
                cleaned_df.to_csv(csv_buf, index=False, encoding="utf-8-sig")
                st.download_button("CSV", csv_buf.getvalue(), f"cleaned_{datetime.now().strftime('%Y%m%d_%H%M')}.csv", "text/csv")

            with col_dl2:
                excel_buf = io.BytesIO()
                with pd.ExcelWriter(excel_buf, engine="openpyxl") as writer:
                    cleaned_df.to_excel(writer, index=False)
                st.download_button("Excel", excel_buf.getvalue(), f"cleaned_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx")

            with col_dl3:
                # PDF Report
                pdf = FPDF()
                pdf.add_page()
                pdf.set_font("Helvetica", size=14)
                pdf.cell(0, 10, "CSV Cleaner Pro - Report", ln=True)
                pdf.set_font("Helvetica", size=11)
                pdf.cell(0, 8, f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M')}", ln=True)
                pdf.cell(0, 8, f"Rows: {original_rows} → {len(cleaned_df)}", ln=True)
                pdf.cell(0, 8, f"Columns: {original_cols} → {cleaned_df.shape[1]}", ln=True)
                pdf.ln(5)
                pdf.cell(0, 8, "Actions:", ln=True)
                for log in logs:
                    pdf.cell(0, 6, f"- {log}", ln=True)
                pdf_bytes = bytes(pdf.output())
                st.download_button("PDF Report", pdf_bytes, f"report_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf", "application/pdf")

# ====================== TAB 2: COMPARE ======================
with tab2:
    st.subheader("📊 Compare Two CSV Files")
    f1 = st.file_uploader("File 1 (Original)", type=["csv"], key="cmp1")
    f2 = st.file_uploader("File 2 (Cleaned or another)", type=["csv"], key="cmp2")

    if f1 and f2:
        df1 = pd.read_csv(f1)
        df2 = pd.read_csv(f2)
        st.write(f"File 1: {df1.shape[0]} rows × {df1.shape[1]} cols")
        st.write(f"File 2: {df2.shape[0]} rows × {df2.shape[1]} cols")

        st.metric("Row difference", df2.shape[0] - df1.shape[0])
        st.metric("Column difference", df2.shape[1] - df1.shape[1])

        common_cols = list(set(df1.columns) & set(df2.columns))
        if common_cols:
            st.write("Common columns:", common_cols)

# ====================== TAB 3: HISTORY & PRESETS ======================
with tab3:
    st.subheader("📜 Cleaning History (this session)")
    if st.session_state.history:
        st.dataframe(pd.DataFrame(st.session_state.history), use_container_width=True)
    else:
        st.info("No history yet.")

    st.subheader("💾 Save / Load Preset")
    preset_data = {
        "remove_duplicates": True,
        "normalize_columns": True,
        "fill_method": "Fill with text (N/A)",
        "auto_fix": True
    }
    st.download_button(
        "Download Current Preset (JSON)",
        json.dumps(preset_data, indent=2),
        "csv_cleaner_preset.json",
        "application/json"
    )

    uploaded_preset = st.file_uploader("Upload Preset JSON", type=["json"])
    if uploaded_preset:
        try:
            data = json.load(uploaded_preset)
            st.success("Preset loaded (apply manually in sidebar for now)")
            st.json(data)
        except:
            st.error("Invalid JSON")

st.markdown("---")
st.caption("CSV Cleaner Pro • Full version with PDF, History, Compare & Paywall")