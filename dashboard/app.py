"""Run with: python -m dashboard.app."""

from __future__ import annotations

import os
from datetime import datetime
from datetime import timezone, timedelta

import pandas as pd
import plotly.graph_objects as go
from dash import Dash, Input, Output, State, dcc, html, no_update

from dashboard.data import market_frames, risk_frames, snapshot, table

TEAL, ORANGE, NAVY = "#147d78", "#dc9250", "#182f40"
app = Dash(__name__, title="Insurance Intelligence · Analytics", suppress_callback_exceptions=True)
server = app.server


def number(value: float | None, *, percent: bool = False) -> str:
    if value is None or pd.isna(value):
        return "—"
    if percent:
        return f"{value * 100:.1f}%"
    for divisor, unit in ((1e12, "nghìn tỷ"), (1e9, "tỷ"), (1e6, "triệu"), (1e3, "nghìn")):
        if abs(value) >= divisor:
            return f"{value/divisor:,.2f} {unit}"
    return f"{value:,.3f}" if value != 0 and abs(value) < 1 else f"{value:,.0f}"


def ratio(numerator: float, denominator: float) -> float | None:
    return numerator / denominator if denominator > 0 else None


def metric(label: str, value: str, detail: str, accent: bool = False):
    return html.Div([html.Span(label, className="metric-label"), html.Strong(value), html.Small(detail)], className="metric accent" if accent else "metric")


def figure(title: str, x: str, y: str) -> go.Figure:
    chart = go.Figure()
    chart.update_layout(
        template="plotly_white", title=None, height=330,
        margin=dict(l=16, r=20, t=20, b=35), font=dict(family="Segoe UI, Arial, sans-serif", color="#536574", size=12),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(title=x, showgrid=False, zeroline=False),
        yaxis=dict(title=y, gridcolor="#edf0f1", zeroline=False),
        legend=dict(orientation="h", y=1.16, x=0, title=None),
        hovermode="x unified", uirevision=title,
    )
    return chart


def chart_card(title: str, subtitle: str, graph_id: str, *, wide: bool = False):
    return html.Section([
        html.Div([html.H3(title), html.P(subtitle)], className="chart-heading"),
        dcc.Graph(id=graph_id, style={"height":"350px"}, config={"displayModeBar": False, "responsive": True}),
    ], className="chart-card wide" if wide else "chart-card")


def page_header(kicker: str, title: str, description: str):
    return html.Div([html.Div(kicker, className="eyebrow"), html.H1(title), html.P(description)], className="page-heading")


def provenance():
    data = snapshot()
    instant = datetime.fromisoformat(data["exported_at_utc"]).astimezone(timezone(timedelta(hours=7)))
    return html.Div([
        html.Span("BẢN CHỤP SQL SERVER", className="source-tag"),
        html.Span(f"Xuất lúc {instant:%d/%m/%Y · %H:%M} (UTC+7)"),
        html.Span("Dữ liệu lịch sử · Không phải dữ liệu thời gian thực", className="source-note"),
    ], className="provenance")


def market_page():
    monthly = table("market", "monthly")
    years = sorted(monthly["month"].str[:4].astype(int).unique())
    states = sorted(monthly["state"].unique())
    return [
        page_header("TRACK A / INSURANCE MARKET", "Bức tranh thị trường bảo hiểm", "Theo dõi phí bảo hiểm, bồi thường và cơ cấu thị trường từ nguồn SUSEP Brazil."),
        html.Div([
            html.Div([html.Label("Khu vực", htmlFor="market-state"), dcc.Dropdown(id="market-state", options=[{"label": "Tất cả các bang", "value": "ALL"}] + [{"label": s, "value": s} for s in states], value="ALL", clearable=False)], className="filter-select"),
            html.Div([html.Label("Giai đoạn", htmlFor="market-years"), dcc.RangeSlider(id="market-years", min=int(years[0]), max=int(years[-1]), step=1, value=[int(years[0]),int(years[-1])], marks={int(y): str(y) for y in years if y % 5 == 0 or y in (years[0],years[-1])}, tooltip={"placement":"bottom","always_visible":False})], className="filter-range"),
            html.Button("Tải CSV ↓", id="market-export", className="button secondary"), dcc.Download(id="market-download"),
        ], className="filter-bar"),
        dcc.Loading(html.Div(id="market-metrics", className="metrics"), type="dot", color=TEAL),
        html.Div([
            chart_card("Phí bảo hiểm & bồi thường", "Xu hướng theo tháng trong phạm vi đã chọn · Đơn vị nguồn", "market-trend", wide=True),
            chart_card("Doanh nghiệp dẫn đầu", "10 doanh nghiệp có tổng phí lớn nhất · Đơn vị nguồn", "market-companies"),
            chart_card("Cơ cấu sản phẩm", "8 nhóm sản phẩm có tổng phí lớn nhất · Đơn vị nguồn", "market-products"),
        ], className="chart-grid"),
        html.Div([html.Strong("Đọc dữ liệu đúng cách. "), "Tỷ lệ bồi thường = tổng claims / tổng premiums, chỉ hiển thị khi tổng premiums > 0. Giá trị âm được giữ theo nguồn. Năm 2023 chỉ có đến tháng 07; không so trực tiếp cả năm với các năm đủ 12 tháng."], className="insight-note"),
    ]


def risk_page():
    states = sorted(table("risk", "segments")["state"].unique())
    metrics = snapshot()["model_metrics"]
    return [
        page_header("TRACK B / MOTOR RISK & ML", "Hiểu rủi ro từ quan sát thực tế", "Phân tích motor-risk và điểm mô hình trên tập held-out riêng từ brvehins1."),
        html.Div([
            html.Div([html.Label("Khu vực", htmlFor="risk-state"), dcc.Dropdown(id="risk-state", options=[{"label":"Tất cả khu vực","value":"ALL"}]+[{"label":s,"value":s} for s in states], value="ALL", clearable=False)], className="filter-select"),
            html.Div([html.Span(f"ROC-AUC {metrics['roc_auc']:.3f}"), html.Span(f"Average precision {metrics['average_precision']:.3f}"), html.Small("Toàn bộ held-out · Không đổi theo bộ lọc khu vực")], className="model-summary"),
            html.Button("Tải CSV ↓", id="risk-export", className="button secondary"), dcc.Download(id="risk-download"),
        ], className="filter-bar"),
        html.Div(id="risk-metrics", className="metrics"),
        html.Div([
            chart_card("Phân bố điểm mô hình", "Số quan sát held-out trong từng dải điểm", "risk-distribution"),
            chart_card("Điểm số & kết quả quan sát", "Tỷ lệ có claim đã quan sát theo dải điểm · Held-out", "risk-observed"),
            chart_card("Rủi ro theo nhóm tuổi", "Tỷ lệ quan sát có claim · Toàn bộ risk DWH", "risk-age"),
            chart_card("Phân bố nhóm hồ sơ", "Nhãn Gender gốc từ dữ liệu · Toàn bộ risk DWH", "risk-gender"),
        ], className="chart-grid"),
        html.Div([html.Strong("Giới hạn của mô hình. "), "Điểm thể hiện liên hệ với HasClaim trong dữ liệu cùng thời điểm. Tập scoring chỉ có 20.000 quan sát held-out, có thể ít hơn sau lọc. Không diễn giải thành xác suất claim tương lai của khách hàng hoặc hợp đồng. Exposure và claim count chỉ áp dụng cho Track B."], className="insight-note"),
    ]


def platform_page():
    data = snapshot()
    perf = pd.DataFrame(data["performance"])
    chart = figure("SQL logical reads", "Số trang dữ liệu được đọc (log scale)", "Workload")
    chart.add_bar(y=perf["workload"], x=perf["before_reads"], name="Trước index", orientation="h", marker_color="#b9c7cc")
    chart.add_bar(y=perf["workload"], x=perf["after_reads"], name="Sau index", orientation="h", marker_color=TEAL)
    chart.update_layout(barmode="group", xaxis_type="log", height=280)
    counts = data["counts"]
    return [
        page_header("PLATFORM / ENGINEERING", "Chất lượng nằm sau mỗi biểu đồ", "Đối soát nguồn dữ liệu và kết quả tối ưu SQL Server đã được đo."),
        html.Div([
            metric("Q1 · Giảm logical reads", "98,94%", "317.528 → 3.364 trang", True),
            metric("Q2 · Giảm logical reads", "98,82%", "317.528 → 3.734 trang"),
            metric("Chi phí hai index", "924,51 MB", "Đổi thêm storage và chi phí ghi"),
            metric("Mô hình triển khai", "2 track", "Market & Motor Risk độc lập"),
        ], className="metrics"),
        html.Section([html.Div([html.H3("Index cải thiện truy vấn đến đâu?"),html.P("Kết quả STATISTICS IO/TIME ngày 24/09/2026 · SQL Server · Warm cache")],className="chart-heading"),dcc.Graph(figure=chart,style={"height":"300px"},config={"displayModeBar":False})],className="chart-card"),
        html.Section([
            html.H3("Đối soát trong bản chụp hiện tại"),
            html.Div([html.Strong("SUSEP Market"),html.Span(f"Staging {counts['market_staging']:,} → Fact {counts['market_fact']:,}"),html.Span("Khớp" if counts['market_staging']==counts['market_fact'] else "Cần kiểm tra",className="reconcile-status")],className="reconcile-row"),
            html.Div([html.Strong("brvehins1 Risk"),html.Span(f"Staging {counts['risk_staging']:,} → Fact {counts['risk_fact']:,}"),html.Span("Khớp" if counts['risk_staging']==counts['risk_fact'] else "Cần kiểm tra",className="reconcile-status")],className="reconcile-row"),
            html.P("Khớp số dòng là một kiểm tra riêng; log Data Quality đầy đủ nằm trong SQL Server. Hai nguồn được điều phối chung bằng Airflow và không có quan hệ nối từng dòng.",className="caption"),
        ],className="quality-panel"),
    ]


app.layout = html.Div([
    dcc.Location(id="url"),
    html.Aside([
        html.A([html.Span("ii",className="brand-mark"),html.Div([html.Strong("INSURANCE"),html.Span("INTELLIGENCE")])],href="/",className="brand"),
        html.Div("ANALYTICS WORKSPACE",className="nav-label"),
        dcc.RadioItems(id="section",value="market",options=[
            {"label":html.Span([html.Span("01",className="nav-number"),"Thị trường bảo hiểm"]),"value":"market"},
            {"label":html.Span([html.Span("02",className="nav-number"),"Motor Risk & ML"]),"value":"risk"},
            {"label":html.Span([html.Span("03",className="nav-number"),"Chất lượng & Hiệu năng"]),"value":"platform"},
        ],className="nav-items"),
        html.Div([html.Div("VỀ DỮ LIỆU",className="nav-label"),html.P("Hai nguồn độc lập.\nMột nền tảng phân tích."),html.Small("SUSEP Market · brvehins1\nPersonal data engineering project")],className="sidebar-footer"),
    ],className="sidebar"),
    html.Main([
        html.Header([html.Span("Insurance Data Platform",className="breadcrumb"),html.Span("DASH / PLOTLY",className="engine-tag")],className="topbar"),
        html.Div(id="source-meta"),
        html.Div(id="page-content"),
        html.Footer([html.Span("Insurance Intelligence"),html.Span("Nguồn: SUSEP & brvehins1 · Các track giữ nguyên grain nguồn")]),
    ],className="workspace"),
],className="shell")


@app.callback(Output("page-content","children"),Output("source-meta","children"),Input("section","value"))
def render_page(section):
    try:
        return {"market":market_page,"risk":risk_page,"platform":platform_page}.get(section,market_page)(),provenance()
    except (OSError, ValueError, KeyError) as exc:
        return html.Div([html.H1("Cần chuẩn bị bản chụp dữ liệu"),html.P(str(exc)),html.Code("python pipeline/export_dashboard.py")],className="insight-note"),""


@app.callback(Output("market-metrics","children"),Output("market-trend","figure"),Output("market-companies","figure"),Output("market-products","figure"),Input("market-state","value"),Input("market-years","value"))
def update_market(state,years):
    monthly,companies,products = market_frames(state,years)
    premium,claims = monthly["premium"].sum(),monthly["claims"].sum()
    cards = [metric("Tổng phí bảo hiểm",number(premium),"Đơn vị nguồn · Trong phạm vi lọc",True),metric("Tổng bồi thường",number(claims),"Đơn vị nguồn · Trong phạm vi lọc"),metric("Tỷ lệ bồi thường",number(ratio(claims,premium),percent=True),"Tổng claims / tổng premiums"),metric("Quan sát thị trường",number(monthly["observations"].sum()),f"{years[0]}–{years[1]} · {state if state!='ALL' else 'Toàn thị trường'}")]
    trend = monthly.groupby("month",as_index=False)[["premium","claims"]].sum()
    plot=figure("Market trend","Tháng","Giá trị (tỷ đơn vị nguồn)")
    plot.add_scatter(x=trend["month"],y=trend["premium"]/1e9,name="Phí bảo hiểm",line=dict(color=TEAL,width=2.5),fill="tozeroy",fillcolor="rgba(20,125,120,0.07)")
    plot.add_scatter(x=trend["month"],y=trend["claims"]/1e9,name="Bồi thường",line=dict(color=ORANGE,width=2))
    plot.update_layout(height=350)
    ranks=[]
    for frame,key,title in [(companies,"company","Company ranking"),(products,"product","Product mix")]:
        names=snapshot()["market"]["company_names" if key=="company" else "product_names"]
        ranked=frame.groupby(key,as_index=False)["premium"].sum().nlargest(10 if key=="company" else 8,"premium").sort_values("premium")
        labels=[names.get(str(x),str(x)) for x in ranked[key]]
        bars=figure(title,"Phí (tỷ đơn vị nguồn)","")
        bars.add_bar(x=ranked["premium"]/1e9,y=[name if len(name)<=28 else name[:27]+"…" for name in labels],orientation="h",marker_color=TEAL if key=="company" else "#719e9a",customdata=labels,hovertemplate="%{customdata}<br>%{x:,.2f} tỷ<extra></extra>")
        bars.update_layout(margin=dict(l=0,r=20,t=8,b=35),hovermode="closest")
        ranks.append(bars)
    return cards,plot,*ranks


@app.callback(Output("risk-metrics","children"),Output("risk-distribution","figure"),Output("risk-observed","figure"),Output("risk-age","figure"),Output("risk-gender","figure"),Input("risk-state","value"))
def update_risk(state):
    segments,scores = risk_frames(state)
    population=scores["observations"].sum()
    cards=[metric("Quan sát rủi ro",number(segments["observations"].sum()),"Toàn bộ risk DWH đã lọc",True),metric("Tổng exposure",number(segments["exposure"].sum()),"Exposure theo đơn vị nguồn"),metric("Claim / exposure",number(ratio(segments["claim_count"].sum(),segments["exposure"].sum())),"Tổng số claim chia tổng exposure"),metric("Điểm mô hình TB",f"{scores['score_sum'].sum()/population:.3f}" if population else "—",f"Chỉ {population:,} quan sát held-out")]
    scores = scores.assign(band=scores["band"].clip(upper=19))
    bands=scores.groupby("band",as_index=False)[["observations","score_sum","positives"]].sum()
    x=(bands["band"]+0.5)/20
    distribution=figure("Score distribution","Điểm mô hình (0–1)","Số quan sát held-out")
    distribution.add_bar(x=x,y=bands["observations"],width=.04,marker_color=TEAL,name="Quan sát")
    distribution.update_xaxes(range=[0,1])
    observed=figure("Observed claim share","Dải điểm mô hình (0–1)","Quan sát có claim (%)")
    observed.add_scatter(x=x,y=100*bands["positives"]/bands["observations"],mode="lines+markers",name="HasClaim quan sát",line=dict(color=ORANGE,width=2))
    observed.update_xaxes(range=[0,1])
    age=segments.groupby("age",as_index=False)[["observations","has_claim"]].sum().sort_values("age")
    age_plot=figure("Driver age","Nhóm tuổi nguồn","Quan sát có claim (%)")
    age_plot.add_bar(x=age["age"],y=100*age["has_claim"]/age["observations"],marker_color=TEAL)
    gender=segments.groupby("gender",as_index=False)["observations"].sum().sort_values("observations")
    gender_plot=figure("Profile labels","Số quan sát","Nhãn Gender nguồn")
    gender_plot.add_bar(x=gender["observations"],y=gender["gender"],orientation="h",marker_color="#719e9a")
    return cards,distribution,observed,age_plot,gender_plot


@app.callback(Output("market-download","data"),Input("market-export","n_clicks"),State("market-state","value"),State("market-years","value"),prevent_initial_call=True)
def download_market(clicks,state,years):
    return dcc.send_data_frame(market_frames(state,years)[0].to_csv,"market-summary.csv",index=False) if clicks else no_update


@app.callback(Output("risk-download","data"),Input("risk-export","n_clicks"),State("risk-state","value"),prevent_initial_call=True)
def download_risk(clicks,state):
    return dcc.send_data_frame(risk_frames(state)[0].to_csv,"risk-summary.csv",index=False) if clicks else no_update


@server.get("/healthz")
def health():
    try:
        data=snapshot()
        return {"status":"ok","data_mode":"warehouse_snapshot","exported_at_utc":data["exported_at_utc"]}
    except (OSError,ValueError,KeyError):
        return {"status":"data_unavailable"},503


if __name__ == "__main__":
    app.run(host=os.getenv("DASH_HOST","127.0.0.1"),port=int(os.getenv("DASH_PORT","8050")),debug=False)
