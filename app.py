import streamlit as st
import numpy as np
import plotly.graph_objects as go

# --- [1] 재질 데이터베이스 (Lotte Chemical TDS 참고치) ---
# 밀도(kg/m^3), 탄성계수(Pa), 포아송비
MATERIALS = {
    "PC+ABS (Standard)": {
        "density": 1150.0, 
        "E": 2400e6, 
        "poisson": 0.38
    },
    "PC+ABS+ED20 (Lotte Chemical)": {
        "density": 1200.0, 
        "E": 2800e6, 
        "poisson": 0.38
    },
    "ABS (High Rigidity)": {
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

def calculate_deflection_mesh(W_mm, H_mm, t_mm, density, E, poisson, mesh_res=50):
    """
    평판 전체의 처짐 분포 계산 (Navier's Solution)
    W_mm: 가로, H_mm: 세로, t_mm: 두께
    """
    # 단위 변환 (mm -> m)
    W_m, H_m, t_m = W_mm / 1000, H_mm / 1000, t_mm / 1000
    
    # 1. 자체 중량 및 등분포 하중(q, N/m^2) 계산
    volume = W_m * H_m * t_m
    weight_kg = volume * density
    q = (weight_kg * 9.81) / (W_m * H_m) 
    
    # 2. 굽힘 강성 (Flexural Rigidity, D)
    D = (E * t_m**3) / (12 * (1 - poisson**2))
    
    # 3. 메쉬 그리드 생성 (m 단위)
    x = np.linspace(0, W_m, mesh_res)
    y = np.linspace(0, H_m, mesh_res)
    X, Y = np.meshgrid(x, y)
    
    # 4. Navier's Series Solution (단순 지지 평판 처짐 공식)
    Z_deflection = np.zeros_like(X)
    max_terms = 15 # 수렴을 위한 급수 항 수
    
    for m in range(1, max_terms, 2):
        for n in range(1, max_terms, 2):
            term_denominator = (m * n * ((m/W_m)**2 + (n/H_m)**2)**2)
            term = (16 * q) / ((np.pi**6) * D * term_denominator)
            Z_deflection += term * np.sin(m * np.pi * X / W_m) * np.sin(n * np.pi * Y / H_m)
    
    return X * 1000, Y * 1000, Z_deflection * 1000, weight_kg

# --- [2] Streamlit UI 구성 ---
st.set_page_config(page_title="TV REAR-COVER 3D 해석", layout="wide")
st.title("📺 TV COVER-REAR 3D 강성 해석 프로그램")
st.info("기구 설계자를 위한 자중 기반 처짐량 예측 시뮬레이터입니다.")

# 사이드바 입력
with st.sidebar:
    st.header("⚙️ 설계 파라미터")
    
    tv_inch = st.number_input("TV 사이즈 (Inch)", min_value=10.0, max_value=110.0, value=65.0, step=1.0)
    thickness = st.slider("부품 두께 (t, mm)", min_value=1.0, max_value=5.0, value=2.5, step=0.1)
    material_choice = st.selectbox("재질 선택 (Lotte Chemical)", list(MATERIALS.keys()), index=1)
    
    st.markdown("---")
    deflection_scale = st.slider("시각화 처짐 배율", min_value=1, max_value=200, value=50, step=5)
    st.caption("※ 실제 처짐은 mm 단위이므로 형상 확인을 위해 배율을 적용합니다.")

# --- [3] 연산 실행 ---
mat_props = MATERIALS[material_choice]

# 1. 가로 세로 치수 결정
W_calc, H_calc = calculate_dimensions(tv_inch)

# 2. 3D 메쉬 및 처짐량 계산 (인자 6개 정확히 전달)
X_mm, Y_mm, Z_def_mm, weight = calculate_deflection_mesh(
    W_calc, 
    H_calc, 
    thickness, 
    mat_props["density"], 
    mat_props["E"], 
    mat_props["poisson"]
)

max_def = np.max(Z_def_mm)

# --- [4] 결과 표시 (2단 레이아웃) ---
col1, col2 = st.columns([1.5, 1])

with col1:
    st.subheader(f"🌐 3D 처짐 분포 (Max: {max_def:.3f} mm)")
    
    # 처짐 형상 시각화 데이터 (Z축은 아래로 처지므로 마이너스)
    Z_visual = -(Z_def_mm * deflection_scale)
    
    fig = go.Figure(data=[go.Surface(
        x=X_mm, y=Y_mm, z=Z_visual,
        surfacecolor=Z_def_mm, # 실제 처짐값으로 색상 표시
        colorscale='Viridis',
        colorbar=dict(title="Deflection(mm)"),
        hovertemplate='W:%{x:.1f}mm<br>H:%{y:.1f}mm<br>Def:%{surfacecolor:.3f}mm<extra></extra>'
    )])

    fig.update_layout(
        scene=dict(
            xaxis_title='Width (mm)',
            yaxis_title='Height (mm)',
            zaxis_title='Deflection (Scaled)',
            aspectmode='data'
        ),
        margin=dict(l=0, r=0, t=0, b=0),
        height=600
    )
    st.plotly_chart(fig, use_container_width=True)

with col2:
    st.subheader("📋 해석 데이터 요약")
    
    st.metric("예상 중량", f"{weight:.2f} kg")
    st.metric("최대 처짐량", f"{max_def:.3f} mm")
    
    with st.expander("상세 물성치 보기"):
        st.write(f"가로: {W_calc:.1f} mm / 세로: {H_calc:.1f} mm")
        st.write(f"밀도: {mat_props['density']} kg/m³")
        st.write(f"탄성계수: {mat_props['E']/1e6:.0f} MPa")
    
    st.markdown("---")
    st.subheader("🛠️ Engineering Advice")
    
    if max_def > 1.5:
        st.error(f"**강성 부족:** 처짐량이 {max_def:.2f}mm로 큽니다. 리브 구조를 추가하거나 두께를 최소 {thickness + 0.5}mm 이상으로 검토하세요.")
    elif max_def > 0.8:
        st.warning("**보강 검토:** 자중 처짐이 다소 발생합니다. 주요 조립 체결부 근처에 보강 리브를 배치하십시오.")
    else:
        st.success("**안정적:** 자중에 의한 처짐이 제어 범위 내에 있습니다.")

    st.caption("본 결과는 단순 지지 조건의 이론적 계산치이며, 실제 사출물의 리브 구조나 구속 조건에 따라 달라질 수 있습니다.")
