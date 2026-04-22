import streamlit as st
import numpy as np
import plotly.graph_objects as go

# --- [1] 재질 데이터베이스 (Lotte Chemical TDS 및 업계 표준 물성치) ---
MATERIALS = {
    "PC+ABS+ED20 (Lotte Chemical)": {
        "density": 1200.0, 
        "E": 2800e6, 
        "poisson": 0.38,
        "desc": "고강성, 난연성 TV 커버 표준 재질"
    },
    "PC+ABS (Standard)": {
        "density": 1150.0, 
        "E": 2400e6, 
        "poisson": 0.38,
        "desc": "범용 PC+ABS 합금 수지"
    },
    "HIPS (High Impact PS)": {
        "density": 1050.0, 
        "E": 1850e6, 
        "poisson": 0.40,
        "desc": "충격 보강 폴리스티렌, 성형성 우수하나 강성 낮음"
    },
    "ABS (High Rigidity)": {
        "density": 1050.0, 
        "E": 2200e6, 
        "poisson": 0.39,
        "desc": "일반 고강성 ABS"
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

def calculate_deflection_mesh(W_mm, H_mm, t_mm, density, E, poisson, mesh_res=50):
    """단순 지지 평판의 Navier's Solution 기반 처짐 연산"""
    W_m, H_m, t_m = W_mm / 1000, H_mm / 1000, t_mm / 1000
    
    # 1. 자체 중량 및 등분포 하중 계산
    volume = W_m * H_m * t_m
    weight_kg = volume * density
    q = (weight_kg * 9.81) / (W_m * H_m) 
    
    # 2. 굽힘 강성 (D)
    D = (E * t_m**3) / (12 * (1 - poisson**2))
    
    # 3. 메쉬 그리드 생성
    x = np.linspace(0, W_m, mesh_res)
    y = np.linspace(0, H_m, mesh_res)
    X, Y = np.meshgrid(x, y)
    
    # 4. Navier's Series Solution 합산
    Z_deflection = np.zeros_like(X)
    max_terms = 15
    
    for m in range(1, max_terms, 2):
        for n in range(1, max_terms, 2):
            term_denominator = (m * n * ((m/W_m)**2 + (n/H_m)**2)**2)
            term = (16 * q) / ((np.pi**6) * D * term_denominator)
            Z_deflection += term * np.sin(m * np.pi * X / W_m) * np.sin(n * np.pi * Y / H_m)
    
    return X * 1000, Y * 1000, Z_deflection * 1000, weight_kg

# --- [2] Streamlit UI 구성 ---
st.set_page_config(page_title="TV REAR-COVER 강성 해석", layout="wide")
st.title("📺 TV COVER-REAR 3D 강성 해석 프로그램")
st.info("요청하신 인치별 프리셋 버튼을 통해 빠르게 자중 처짐량을 확인할 수 있습니다.")

with st.sidebar:
    st.header("⚙️ 설계 파라미터")
    
    # [인치 선택 버튼 적용]
    st.write("**TV 사이즈 선택 (Inch)**")
    inch_options = [43, 55, 65, 75, 85, 98, 115, 130]
    # 가로형 버튼 느낌을 주기 위해 radio 사용 (또는 selectbox)
    selected_inch = st.radio("인치 프리셋", inch_options, index=2, horizontal=True)
    
    st.markdown("---")
    thickness = st.slider("부품 두께 (t, mm)", min_value=1.0, max_value=6.0, value=2.5, step=0.1)
    
    material_choice = st.selectbox("재질 선택", list(MATERIALS.keys()), index=0)
    st.caption(f"ℹ️ {MATERIALS[material_choice]['desc']}")
    
    st.markdown("---")
    deflection_scale = st.slider("시각화 처짐 배율", min_value=1, max_value=500, value=100, step=10)

# --- [3] 연산 및 결과 시각화 ---
mat_props = MATERIALS[material_choice]
W_calc, H_calc = calculate_dimensions(selected_inch)
X_mm, Y_mm, Z_def_mm, weight = calculate_deflection_mesh(
    W_calc, H_calc, thickness, mat_props["density"], mat_props["E"], mat_props["poisson"]
)
max_def = np.max(Z_def_mm)

col1, col2 = st.columns([1.5, 1])

with col1:
    st.subheader(f"🌐 {selected_inch}인치 3D 처짐 분포 (Max: {max_def:.3f} mm)")
    # 시각화 데이터 (Z축 하향 처짐)
    Z_visual = -(Z_def_mm * deflection_scale)
    
    fig = go.Figure(data=[go.Surface(
        x=X_mm, y=Y_mm, z=Z_visual,
        surfacecolor=Z_def_mm,
        colorscale='Viridis',
        colorbar=dict(title="실제 처짐(mm)"),
        hovertemplate='가로:%{x:.0f}mm<br>세로:%{y:.0f}mm<br>처짐:%{surfacecolor:.3f}mm<extra></extra>'
    )])

    fig.update_layout(
        scene=dict(
            xaxis_title='Width (mm)',
            yaxis_title='Height (mm)',
            zaxis_title='Scaled Deflection',
            aspectmode='data' # 실제 가로/세로 비율 유지
        ),
        margin=dict(l=0, r=0, t=0, b=0), height=650
    )
    st.plotly_chart(fig, use_container_width=True)

with col2:
    st.subheader("📋 해석 결과 요약")
    
    # 주요 지표 메트릭
    m_col1, m_col2 = st.columns(2)
    m_col1.metric("선택 사이즈", f"{selected_inch} inch")
    m_col2.metric("예상 중량", f"{weight:.2f} kg")
    
    st.metric("최대 처짐량 (Center)", f"{max_def:.3f} mm")
    
    with st.expander("세부 데이터 확인"):
        st.write(f"**규격:** {W_calc:.1f} x {H_calc:.1f} mm")
        st.write(f"**재질:** {material_choice}")
        st.write(f"**탄성계수:** {mat_props['E']/1e6:.0f} MPa")
        st.write(f"**면적:** {(W_calc*H_calc/1000000):.2f} m²")

    st.markdown("---")
    st.subheader("🛠️ Engineering Advice")
    
    # 처짐량에 따른 설계 가이드 로직
    if max_def > 1.5:
        st.error(f"**강성 위험:** {selected_inch}인치의 거대 사이즈 대비 두께({thickness}mm)가 얇습니다. 중앙부 처짐이 심하므로 리브 보강 및 두께 상향이 필수입니다.")
    elif max_def > 0.7:
        st.warning("**주의:** 자중으로 인한 처짐이 관찰됩니다. 조립 시 하중 분산을 위해 보강 구조를 검토하십시오.")
    else:
        st.success("**안정:** 현재 재질 및 두께 조건에서 강성이 양호합니다.")
    
    st.info("💡 **Tip:** 85인치 이상의 초대형 모델은 자중뿐만 아니라 사출 시 수축 변형(Warpage) 관리가 중요하므로 금형 냉각 레이아웃도 함께 고려하세요.")
