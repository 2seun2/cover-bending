import streamlit as st
import numpy as np
import plotly.graph_objects as go

# --- [1] 재질 데이터베이스 (Lotte Chemical TDS 참고치 적용) ---
# 밀도(kg/m^3), 탄성계수(Pa), 포아송비
MATERIALS = {
    "PC+ABS (일반 상용)": {
        "density": 1150.0, 
        "E": 2400e6, 
        "poisson": 0.38
    },
    "PC+ABS+ED20 (난연/강화 그레이드 참고)": {
        "density": 1200.0, 
        "E": 2800e6, 
        "poisson": 0.38
    },
    "ABS (비교용)": {
        "density": 1050.0, 
        "E": 2200e6, 
        "poisson": 0.39
    }
}

def calculate_dimensions(inch):
    """TV 인치를 기반으로 16:9 비율의 가로(W), 세로(H) mm 치수 계산"""
    diag_mm = inch * 25.4
    ratio_w, ratio_h = 16, 9
    diag_ratio = np.sqrt(ratio_w**2 + ratio_h**2)
    
    W = diag_mm * (ratio_w / diag_ratio)
    H = diag_mm * (ratio_h / diag_ratio)
    return W, H

def calculate_deflection(W, H, t, density, E, poisson):
    """
    평판 처짐 공식(Roark's Formulas 적용)
    - 4변 단순 지지(Simply Supported), 등분포 하중(자중) 작용 조건
    - a/b (가로/세로) 비율이 16:9 (약 1.77)일 때의 계수 alpha 적용 (약 0.010)
    """
    # 단위 변환 (mm -> m)
    W_m, H_m, t_m = W / 1000, H / 1000, t / 1000
    
    # 1. 자체 중량 및 등분포 하중(Pressure) 계산
    volume = W_m * H_m * t_m
    weight_kg = volume * density
    # 단위 면적당 하중 (N/m^2)
    q = (weight_kg * 9.81) / (W_m * H_m) 
    
    # 2. 굽힘 강성 (Flexural Rigidity, D)
    D = (E * t_m**3) / (12 * (1 - poisson**2))
    
    # 3. 최대 처짐량 계산 (b는 짧은 변인 H_m)
    # alpha 계수는 a/b = 1.77 기준 약 0.0101 적용
    alpha = 0.0101 
    deflection_m = (alpha * q * H_m**4) / D
    
    return weight_kg, deflection_m * 1000 # 처짐량 mm 단위로 반환

# --- [2] Streamlit UI 구성 ---
st.set_page_config(page_title="TV COVER-REAR 처짐 해석기", layout="wide")
st.title("📺 TV COVER-REAR 강도 해석 및 처짐량 계산기")
st.markdown("플라스틱(PC+ABS) 사출품의 자중에 의한 중앙부 최대 처짐량을 예측합니다.")

# 사이드바 입력
with st.sidebar:
    st.header("입력 변수 (Input Parameters)")
    
    # 인치 선택 (사용자 직접 입력도 가능하도록 number_input 사용)
    tv_inch = st.number_input("TV 사이즈 (Inch)", min_value=10.0, max_value=120.0, value=65.0, step=1.0)
    
    # 두께 선택
    thickness = st.slider("부품 두께 (t, mm)", min_value=1.0, max_value=5.0, value=2.5, step=0.1)
    
    # 재질 선택
    material_choice = st.selectbox("수지 재질 (Material)", list(MATERIALS.keys()), index=1)
    
    st.markdown("---")
    st.markdown("**기계공학적 모델링 조건**\n* 4면 끝단 단순 지지 (Simply Supported)\n* 자중에 의한 등분포 하중 적용")

# 데이터 매핑
mat_props = MATERIALS[material_choice]
W, H = calculate_dimensions(tv_inch)
weight, max_deflection = calculate_deflection(W, H, thickness, mat_props["density"], mat_props["E"], mat_props["poisson"])

# --- [3] 메인 화면 결과 출력 ---
col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("📊 시각화 및 형상 정보")
    
    # Plotly를 이용한 2D 평면도 및 지지점/처짐점 시각화
    fig = go.Figure()
    
    # COVER 외곽선
    fig.add_trace(go.Scatter(x=[0, W, W, 0, 0], y=[0, 0, H, H, 0], 
                             mode="lines", name="COVER 외곽선", line=dict(color="blue", width=2)))
    
    # 지지점 (4개 모서리)
    fig.add_trace(go.Scatter(x=[0, W, W, 0], y=[0, 0, H, H], 
                             mode="markers", name="지지점 (Supported)", marker=dict(color="green", size=10, symbol="square")))
    
    # 최대 처짐 발생점 (중앙)
    fig.add_trace(go.Scatter(x=[W/2], y=[H/2], 
                             mode="markers+text", name="최대 처짐점", text=["Max Deflection"], textposition="top center",
                             marker=dict(color="red", size=12, symbol="x")))

    fig.update_layout(
        xaxis=dict(title="가로 W (mm)", range=[-W*0.1, W*1.1], constrain='domain'),
        yaxis=dict(title="세로 H (mm)", scaleanchor="x", scaleratio=1), # 실제 16:9 비율 유지
        showlegend=True,
        margin=dict(l=0, r=0, t=30, b=0),
        height=400
    )
    st.plotly_chart(fig, use_container_width=True)

with col2:
    st.subheader("💡 해석 결과 요약")
    
    # 결과 지표 표시
    st.metric(label="COVER-REAR 예상 무게", value=f"{weight:.2f} kg")
    st.metric(label="중앙부 최대 처짐량", value=f"{max_deflection:.3f} mm", delta="단순 지지 조건 기준", delta_color="off")
    
    st.markdown("---")
    st.markdown("### 세부 제원 및 물성치")
    st.write(f"- **가로(W) x 세로(H):** {W:.1f} mm x {H:.1f} mm")
    st.write(f"- **적용 재질:** {material_choice}")
    st.write(f"- **밀도 (Density):** {mat_props['density']} kg/m³")
    st.write(f"- **탄성계수 (Young's Modulus):** {mat_props['E'] / 1e6:.0f} MPa")
    
    # 강성 평가 코멘트
    st.markdown("### 🛠️ 설계 제언")
    if max_deflection > 2.0:
        st.error("⚠️ **경고:** 자체 하중만으로도 처짐량이 2.0mm를 초과합니다. 내부 리브(Rib) 보강이나 두께 증대가 필요합니다.")
    elif max_deflection > 1.0:
        st.warning("⚡ **주의:** 처짐이 발생할 수 있으므로 조립 공차 및 외관 평가 시 주의가 필요합니다.")
    else:
        st.success("✅ **안정:** 자중으로 인한 처짐량이 기준치(1.0mm) 이내로 양호한 수준입니다.")
