from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP_SOURCE = (ROOT / "app.py").read_text(encoding="utf-8")
DASHBOARD_SOURCE = (ROOT / "galleyeye" / "dashboard.py").read_text(encoding="utf-8")
THEME_CONFIG = (Path(__file__).resolve().parents[1] / ".streamlit" / "config.toml")


def test_theme_does_not_override_streamlit_native_controls():
    for selector in (".stApp", "stMetric", "stVerticalBlockBorderWrapper", ".stButton"):
        assert selector not in APP_SOURCE
    assert "!important" not in APP_SOURCE


def test_sidebar_is_a_primary_colored_navigation_surface():
    assert '[data-testid="stSidebarContent"]' in DASHBOARD_SOURCE
    assert '[data-testid="stSidebarUserContent"]' in DASHBOARD_SOURCE
    assert 'background:{SIDEBAR_BLUE}' in DASHBOARD_SOURCE
    assert 'SIDEBAR_BLUE = "#0F172A"' in DASHBOARD_SOURCE
    assert 'SIDEBAR_HOVER = "#25334A"' in DASHBOARD_SOURCE
    assert 'SIDEBAR_SELECTED = "#2563EB"' in DASHBOARD_SOURCE
    assert 'SIDEBAR_FOREGROUND = "#F8FAFC"' in DASHBOARD_SOURCE
    assert '.st-key-nav [role="radiogroup"] label:hover' in DASHBOARD_SOURCE
    assert 'label:has(input:checked)' in DASHBOARD_SOURCE
    assert 'background:{SIDEBAR_SELECTED}' in DASHBOARD_SOURCE
    assert 'label:focus-within' in DASHBOARD_SOURCE
    assert 'label > div:first-child {{flex:0 0 auto}}' in DASHBOARD_SOURCE
    assert 'label_visibility="collapsed"' in DASHBOARD_SOURCE
    assert 'sidebar-section-label">Navigation' in DASHBOARD_SOURCE


def test_dashboard_styles_are_emitted_during_each_render():
    render_body = DASHBOARD_SOURCE.split("def render_dashboard", 1)[1]
    assert "apply_dashboard_styles()" in render_body


def test_theme_uses_a_simple_non_gradient_shell():
    assert "linear-gradient" not in DASHBOARD_SOURCE
    config=THEME_CONFIG.read_text(encoding="utf-8")
    assert 'base = "light"' in config
    assert 'primaryColor = "#2563EB"' in config
    assert 'textColor = "#172033"' in config


def test_overview_buttons_use_streamlit_primary_style():
    assert 'st.button("Open flight detail"' in DASHBOARD_SOURCE
    assert 'type="primary"' in DASHBOARD_SOURCE


def test_dashboard_uses_shared_table_formats_and_precise_domain_labels():
    assert "table_column_config" in DASHBOARD_SOURCE
    assert "items.served_quantity.gt(0)" in DASHBOARD_SOURCE
    assert ':.3f} kg' not in DASHBOARD_SOURCE
    assert 'b.metric("Waste"' not in DASHBOARD_SOURCE
    assert 'name="Waste / 100 passengers"' not in DASHBOARD_SOURCE
