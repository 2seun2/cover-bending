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

def calculate_deflection_mesh(W, H, t, density, E, poisson, mesh_res=50):
    """
    평판 전체의 처짐 분포 계산 (3D 시각화용 메쉬 생성)
    - 4변 단순 지지(Simply Supported), 자중 등분포 하중 조건
    - Navier's Solution을 이용한 급수 해법 적용 (가장 정확한 이론값)
    """
    # 단위 변환 (mm -> m)
    W_m, H_m, t_m = W / 1000, H / 1000, t / 1000
    
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
    
    # 4. Navier's Series Solution을 이용한 각 점의 처짐(Z) 계산
    # 급수를 m, n = 1, 3, 5... 로 19항까지 합산하여 수렴시킴
    Z_deflection = np.zeros_like(X)
    max_terms = 20 # 급수 항 수
    
    for m in range(1, max_terms, 2):
        for n in range(1, max_terms, 2):
            term_denominator = (m*n * ((m/W_m)**2 + (n/H_m)**2)**2)
            term = (16 * q) / ((np.pi**6) * D * term_denominator)
            Z_deflection += term * np.sin(m * np.pi * X / W_m) * np.sin(n * np.pi * Y / H_m)
    
    # 최종 결과 단위를 mm로 변환 (W, H는 원래 mm이므로 X, Y만 변환)
    return W, H, X * 1000, Y * 1000, Z_deflection * 1000, weight_kg

# --- [2] Streamlit UI 구성 ---
st.set_page_config(page_title="TV REAR-COVER 3D 강성 해석", layout="wide")
st.title("📺 TV COVER-REAR 3D 강성 해석 및 자중 처짐 계산기")
st.markdown("롯데케미칼 PC+ABS 수지 물성 기반, 자중에 의한 **3D 처짐 형상**을 예측합니다.")

# 사이드바 입력
with st.sidebar:
    st.header("🔧 입력 변수 (Input)")
    
    # 인치 선택 (사용자 직접 입력도 가능하도록 number_input 사용)
    tv_inch = st.number_input("TV 사이즈 (Inch)", min_value=10.0, max_value=120.0, value=55.0, step=1.0)
    
    # 두께 선택
    thickness = st.slider("부품 두께 (t, mm)", min_value=1.0, max_value=5.0, value=2.5, step=0.1)
    
    # 재질 선택
    material_choice = st.selectbox("수지 재질 (Material)", list(MATERIALS.keys()), index=1)
    
    # 3D 시각화 배율 (처짐량이 너무 작아 안 보일 때를 대비)
    st.markdown("---")
    deflection_scale = st.slider("3D 처짐 시각화 배율 (Scale)", min_value=1, max_value=100, value=20, step=1)
    st.caption("※ 실제 처짐량(mm)이 작으므로, 형상 변화를 잘 보이게 하기 위한 시각적 배율입니다.")

# 데이터 계산 (Navier 급수 해법 적용된 메쉬 데이터)
mat_props = MATERIALS[material_choice]
W_mm, H_mm, X_mm, Y_mm, Z_deflection_mm, weight = calculate_deflection_mesh(
    tv_inch, thickness, mat_props["density"], mat_props["E"], mat_props["poisson"]
)

# 최대 처짐량 (배열의 최댓값)
max_deflection = np.max(Z_deflection_mm)

# --- [3] 메인 화면 결과 출력 ---
col1, col2 = st.columns([1.5, 1])

with col1:
    st.subheader(f"🌐 3D 처짐 형상 시각화 (배율: {deflection_scale}x)")
    
    # 3D 시각화를 위한 Z축 데이터 가공:
    # 플라스틱 부품의 기본 평면(Z=0)에서 처짐량(Z_deflection)을 뺍니다. (아래로 처지게)
    # 여기에 시각화 배율(Scale)을 곱합니다.
    Z_visual = -(Z_deflection_mm * deflection_scale)
    
    # Plotly 3D Surface Plot 생성
    fig = go.Figure(data=[go.Surface(
        x=X_mm, y=Y_mm, z=Z_visual,
        colorscale='Turbid', # 처짐량에 따른 색상 (Contour)
        colorbar=dict(title="실제 처짐(mm)", titleside="right"),
        contours_z=dict(show=True, usecolormap=True, highlightcolor="white", project_z=True), # 바닥에 등고선 표시
        surfacecolor=Z_deflection_mm, # 색상 기준은 배율 안 곱한 실제 처짐량으로
        hovertemplate='W: %{x:.1f}mm<br>H: %{y:.1f}mm<br>처짐: %{surfacecolor:.3f}mm<extra></extra>'
    )])
    
    # 지지점 (4개 모서리) 표시
    # fig.add_trace(go.Scatter3d(x=[0, W_mm, W_mm, 0], y=[0, 0, H_mm, H_mm], z=[0, 0, 0, 0], 
    #                          mode="markers", name="지점", marker=dict(color="black", size=5, symbol="square")))

    # 3D 레이아웃 설정
    fig.update_layout(
        scene=dict(
            xaxis=dict(title="가로 W (mm)", range=[0, W_mm]),
            yaxis=dict(title="세로 H (mm)", range=[0, H_mm]),
            zaxis=dict(title="처짐(Scaled)", range=[-max_deflection * deflection_scale * 1.2, max_deflection * deflection_scale * 0.2]),
            aspectmode='data' # 실제 가로/세로 비율 유지
        ),
        margin=dict(l=0, r=0, t=0, b=0),
        height=600,
        camera=dict(eye=dict(x=1.2, y=1.2, z=0.8)) # 초기 카메라 앵글
    )
    
    st.plotly_chart(fig, use_container_width=True)

with col2:
    st.subheader("💡 해석 결과 요약")
    
    # 결과 지표 표시
    st.metric(label="COVER-REAR 예상 무게", value=f"{weight:.2f} kg")
    st.metric(label="중앙부 **최대 처짐량**", value=f"{max_deflection:.3f} mm", delta="단순 지지 조건 기준", delta_color="off")
    
    st.markdown("---")
    st.markdown("### 📋 세부 제원 및 물성치")
    st.write(f"- **외곽 치수:** {W_mm:.1f} mm x {H_mm:.1f} mm")
    st.write(f"- **적용 재질:** {material_choice}")
    st.write(f"- **밀도 (Density):** {mat_props['density']} kg/m³")
    st.write(f"- **굴곡탄성률 (Flexural Modulus):** {mat_props['E'] / 1e6:.0f} MPa")
    
    # 강성 평가 코멘트
    st.markdown("---")
    st.markdown("### 🛠️ 기구 설계 제언")
    if max_deflection > 2.0:
        st.error(f"⚠️ **⚠️ 경고 (고위험):** 자중 처짐({max_deflection:.2f}mm)이 과다합니다. TV REAR COVER로 사용하기에 강성이 부족합니다. **전면적인 리브(Rib) 보강 레이아웃** 설계 또는 두께 증대가 필수적입니다.")
    elif max_deflection > 1.0:
        st.warning(f"⚡ **주의 (보강 필요):** 처짐량이 1mm를 초과합니다. 대형 TV의 경우 외관 불량이나 내부 부품 간섭이 발생할 수 있으므로, **주요 영역에 보강 리브**를 추가하는 것을 권장합니다.")
    else:
        st.success(f"✅ **안정 (양호):** 자중에 의한 처짐량이 기준치(1.0mm) 이내로 양호한 수준입니다. 기본 사출 강성은 확보된 것으로 보입니다.")
