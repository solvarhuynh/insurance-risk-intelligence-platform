"""Insurance analytics workspace. Run with: python -m dashboard.app."""

from __future__ import annotations

import os
import re
from datetime import datetime, timedelta, timezone
from urllib.parse import quote

import pandas as pd
import plotly.graph_objects as go
from dash import Dash, Input, Output, State, ctx, dcc, html, no_update

from dashboard.data import latest_market_comparison, market_frames, risk_frames, snapshot, table

BLUE, TEAL, ORANGE, INK, MUTED = "#003366", "#007c83", "#b66a45", "#13334b", "#61768a"
SCORE, CONTEXT = "#7560a6", "#93a5b5"
PALE_BLUE, GRID = "#9db9cb", "#e5edf2"
EXPLORER_PAGE_SIZE = 15
STATES = {
    "AC": "Acre", "AL": "Alagoas", "AM": "Amazonas", "AP": "Amapá", "BA": "Bahia",
    "CE": "Ceará", "DF": "Federal District", "ES": "Espírito Santo", "GO": "Goiás",
    "MA": "Maranhão", "MG": "Minas Gerais", "MS": "Mato Grosso do Sul", "MT": "Mato Grosso",
    "PA": "Pará", "PB": "Paraíba", "PE": "Pernambuco", "PI": "Piauí", "PR": "Paraná",
    "RJ": "Rio de Janeiro", "RN": "Rio Grande do Norte", "RO": "Rondônia", "RR": "Roraima",
    "RS": "Rio Grande do Sul", "SC": "Santa Catarina", "SE": "Sergipe", "SP": "São Paulo", "TO": "Tocantins",
}
# Official line codes stay visible; the snapshot retains the original source names.
PRODUCTS = {
    "0111": "Fire", "0114": "Home insurance", "0116": "Condominium", "0118": "Business insurance",
    "0141": "Business interruption", "0167": "Engineering risks", "0171": "Miscellaneous risks",
    "0195": "Extended warranty", "0196": "Named & operational risks", "0351": "General liability",
    "0531": "Motor own damage", "0553": "Motor liability", "0588": "DPVAT motor cover",
    "0775": "Public-sector surety", "0776": "Private-sector surety", "0977": "Credit life",
    "0982": "Personal accident", "0991": "Individual life", "0992": "Individual VGBL plans",
    "0993": "Group life", "0994": "VGBL plans", "1391": "Life insurance", "1392": "VGBL & related plans",
}
PRODUCT_SHORT = {
    "0118": "Business cover", "0141": "Business interruption", "0167": "Engineering",
    "0171": "Other risks", "0195": "Extended warranty", "0196": "Operational risks",
    "0531": "Motor own damage", "0553": "Motor liability", "0588": "DPVAT motor",
    "0775": "Public surety", "0776": "Private surety", "0977": "Credit life",
    "0982": "Personal accident", "0991": "Individual life", "0992": "Individual VGBL",
    "0993": "Group life", "0994": "VGBL plans", "1391": "Life insurance", "1392": "VGBL & related plans",
}
ICONS = {
    "grid": '<rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/>',
    "risk": '<path d="M3 18l5-6 4 3 8-10M15 5h5v5M3 22h18"/>',
    "database": '<ellipse cx="12" cy="5" rx="8" ry="3"/><path d="M4 5v7c0 4 16 4 16 0V5M4 12v7c0 4 16 4 16 0v-7"/>',
    "shield": '<path d="M12 2l8 3v6c0 5-4 8-8 11-4-3-8-6-8-11V5zM8 12l3 3 5-6"/>',
    "download": '<path d="M12 3v12m-5-5l5 5 5-5M4 16v5h16v-5"/>',
    "calendar": '<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M7 3v5m10-5v5M3 11h18m-13 4h2m4 0h2"/>',
    "globe": '<circle cx="12" cy="12" r="9"/><ellipse cx="12" cy="12" rx="4" ry="9"/><path d="M3 12h18"/>',
    "premium": '<path d="M4 20V10m6 10V5m6 15v-7m5 7H2M3 6l6-4 7 5 5-4"/>',
    "claims": '<path d="M8 3H5v18h14V7l-4-4H8zM14 3v5h5M8 12h7m-7 4h7"/>',
    "percent": '<circle cx="6.5" cy="6.5" r="3"/><circle cx="17.5" cy="17.5" r="3"/><path d="M4 20L20 4"/>',
    "rows": '<path d="M8 5h13M8 12h13M8 19h13M3 5h.01M3 12h.01M3 19h.01"/>',
    "reset": '<path d="M3 10a9 9 0 1 1 2 8M3 4v6h6"/>',
    "check": '<path d="M5 12l4 4L19 6"/>',
    "info": '<circle cx="12" cy="12" r="9"/><path d="M12 11v6m0-10h.01"/>',
}

app = Dash(__name__, title="Insurance Intelligence | Analytics", suppress_callback_exceptions=True,
           update_title=None, meta_tags=[{"name": "viewport", "content": "width=device-width, initial-scale=1"}])
server = app.server
app.index_string = app.index_string.replace("<html>", '<html lang="en">')


def icon(name):
    svg = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="black" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">{ICONS[name]}</svg>'
    mask = f'url("data:image/svg+xml,{quote(svg)}")'
    return html.Span(className="icon", style={"maskImage": mask, "WebkitMaskImage": mask}, **{"aria-hidden": "true"})


def number(value: float | None, *, percent: bool = False) -> str:
    if value is None or pd.isna(value):
        return "—"
    if percent:
        return f"{value * 100:.1f}%"
    for divisor, unit in ((1e12, "T"), (1e9, "B"), (1e6, "M"), (1e3, "K")):
        if abs(value) >= divisor:
            return f"{value / divisor:,.2f}{unit}"
    return f"{value:,.3f}" if value != 0 and abs(value) < 1 else f"{value:,.0f}"


def ratio(numerator, denominator):
    return numerator / denominator if denominator > 0 else None


def metric(label, value, detail, *, symbol="rows", tone="neutral", exact=None, comparison=None):
    display = [value[:-3], html.Span("MB", className="metric-unit")] if value.endswith(" MB") else value
    return html.Div([
        html.Div([icon(symbol), html.Span(label, className="metric-label")], className="metric-top"),
        html.Strong(display, title=str(exact) if exact is not None else value), html.Small(detail), comparison,
    ], className=f"metric {tone}")


def market_change(comparison, key, *, lower_is_better=False):
    if not comparison:
        return None
    change = comparison[key]
    rounded = round(change, 1)
    favorable = change < 0 if lower_is_better else change > 0
    tone = "neutral" if rounded == 0 else "positive" if favorable else "negative"
    unit = " pp" if lower_is_better else "%"
    meaning = "Claims / premiums movement; lower is favorable" if lower_is_better else "Premium volume movement; higher means growth"
    return html.Div([
        html.Span(f"{rounded:+.1f}{unit} · latest year", className=f"metric-change {tone}"),
        html.Span(comparison["period"], className="comparison-period"),
    ], className="metric-comparison", title=f"{meaning}. Same calendar months: {comparison['period']}. Totals above cover the selected range.")


def figure(key, x, y):
    chart = go.Figure()
    chart.update_layout(
        template="plotly_white", title=None, autosize=True,
        margin=dict(l=12, r=28, t=24, b=20),
        font=dict(family="Inter, Segoe UI, sans-serif", color=MUTED, size=12),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(title=dict(text=x, standoff=16), showgrid=False, zeroline=False, automargin=True,
                   tickfont=dict(size=11)),
        yaxis=dict(title=dict(text=y, standoff=12), gridcolor=GRID, zeroline=False,
                   automargin=True, tickfont=dict(size=11), nticks=5),
        legend=dict(orientation="h", y=1.02, yanchor="bottom", x=0, title=None, font=dict(size=11)),
        hovermode="x unified", hoverlabel=dict(bgcolor="white", font_size=12, font_color=INK),
        uirevision=key, separators=".,", bargap=.32,
    )
    return chart


def graph(graph_id=None, *, chart=None):
    props = {"id": graph_id} if graph_id else {}
    if chart is not None:
        props["figure"] = chart
    return html.Div(dcc.Graph(**props, className="chart", responsive=True,
                             config={"displayModeBar": "hover", "displaylogo": False, "scrollZoom": False,
                                     "modeBarButtonsToRemove": ["select2d", "lasso2d", "autoScale2d"],
                                     "toImageButtonOptions": {"format": "png", "scale": 2}}), className="chart-frame")


def chart_card(title, subtitle, graph_id, *, wide=False, controls=None, headline_id=None, footer=None):
    heading = html.H2(title, id=headline_id) if headline_id else html.H2(title)
    return html.Section([
        html.Div([html.Div([heading, html.P(subtitle)]), controls], className="chart-heading"), graph(graph_id),
        html.Div(footer, className="chart-footnote") if footer else None,
    ], className="chart-card wide" if wide else "chart-card")


def page_header(kicker, title, description, scope_label, scope_value, scope_note):
    return html.Div([
        html.Div([html.Div(kicker, className="eyebrow"), html.H1(title), html.P(description)]),
        html.Div([html.Span(scope_label), html.Strong(scope_value), html.Small(scope_note)], className="coverage"),
    ], className="page-heading")


def provenance():
    instant = datetime.fromisoformat(snapshot()["exported_at_utc"]).astimezone(timezone(timedelta(hours=7)))
    return html.Div([html.Span("Historical snapshot", className="snapshot-badge"),
                     html.Span(f"Exported {instant:%d %b %Y, %H:%M} UTC+7", className="snapshot-time")], className="provenance")


def state_filter(track, states):
    return html.Div([
        html.Label([icon("globe"), "Geography"], htmlFor=f"{track}-state"),
        dcc.Dropdown(id=f"{track}-state", options=[{"label": "All states", "value": "ALL"}] + [
            {"label": f"{s} · {STATES.get(s, 'Unknown')}", "value": s} for s in states
        ], value="ALL", clearable=False, persistence=True, persistence_type="session"),
    ], className="filter-select")


def export_button(track):
    return html.Div([html.Button([icon("download"), "Export CSV"], id=f"{track}-export", className="button primary"),
                     dcc.Download(id=f"{track}-download")], className="export-action")


def market_page():
    monthly = table("market", "monthly")
    years = sorted(monthly["month"].str[:4].astype(int).unique())
    return [
        page_header("MARKET INTELLIGENCE / TRACK A", "Insurance market overview",
                    "Follow premiums and claims over time, then see which insurers and products shape that volume.",
                    "SOURCE COVERAGE", "Jan 2003 — Jul 2023", "SUSEP · 27 Brazilian states"),
        html.Div([
            state_filter("market", sorted(monthly["state"].unique())),
            html.Div([
                html.Label([icon("calendar"), "Year range"], htmlFor="market-years"),
                dcc.RangeSlider(id="market-years", min=int(years[0]), max=int(years[-1]), step=1,
                                value=[int(years[0]), int(years[-1])],
                                marks={int(y): str(y) for y in years if y % 5 == 0 or y in (years[0], years[-1])},
                                tooltip={"placement": "bottom", "always_visible": False},
                                persistence=True, persistence_type="session"),
            ], className="filter-range"),
            html.Button([icon("reset"), "Reset"], id="market-reset", className="button quiet"), export_button("market"),
        ], className="filter-bar"),
        html.Div(id="market-metrics", className="metrics", **{"aria-live": "polite"}),
        html.Div([
            chart_card("Premiums and claims, in perspective",
                       "Compare reported premiums and claims over the selected period. Values in billions of source units.",
                       "market-trend", wide=True, headline_id="market-takeaway",
                       controls=dcc.RadioItems(id="market-grain", options=[{"label": "Monthly", "value": "monthly"},
                                              {"label": "Annual", "value": "annual"}], value="monthly", className="segmented"),
                       footer="2023 includes January–July only. Claims / premiums is a descriptive ratio, not a profit margin."),
            chart_card("Which companies lead premium volume?",
                       "Top 10 insurers; premiums in billions of source units. Hover for source names and shares of all selected premiums.",
                       "market-companies"),
            chart_card("Where is premium volume concentrated?",
                       "Top 8 product lines; premiums in billions of source units. The same selection, viewed by product rather than insurer.",
                       "market-products"),
        ], className="chart-grid"),
        html.Div(id="market-story", className="insight-strip", **{"aria-live": "polite"}),
    ]


def risk_page():
    metrics = snapshot()["model_metrics"]
    return [
        page_header("MOTOR ANALYTICS / TRACK B", "Motor risk & model insights",
                    "Read exposure and claim patterns first, then compare held-out model scores with observed outcomes.",
                    "MODEL EVALUATION", f"{metrics['rows']:,} held-out observations", "Historical evaluation · September 2026"),
        html.Div([
            state_filter("risk", sorted(table("risk", "segments")["state"].unique())),
            html.Button([icon("reset"), "Reset"], id="risk-reset", className="button quiet"), export_button("risk"),
        ], className="filter-bar risk-filter"),
        html.Div([html.Span("01 / OBSERVED PORTFOLIO", className="eyebrow"),
                  html.H2("Start with the warehouse population"),
                  html.P("All filtered motor observations. Compare claim share by age, with the source-label mix as context.")],
                 className="section-heading"),
        html.Div(id="risk-metrics", className="metrics warehouse-metrics", **{"aria-live": "polite"}),
        html.Div([
            chart_card("Observed claim share varies by age group", "Share of observations with HasClaim, across the full filtered risk warehouse.", "risk-age"),
            chart_card("The observation mix behind the analysis", "Counts by source Gender label, including corporate and unknown records.", "risk-gender"),
        ], className="chart-grid"),
        html.Div([
            html.Div([html.Span("02 / HELD-OUT EVALUATION", className="eyebrow"),
                      html.H2("Then test what the model score separates"),
                      html.P("A separate held-out sample. Geography filters these plots; historical evaluation metrics below stay fixed.")]),
            html.Div(id="risk-model-metric", **{"aria-live": "polite"}),
        ], className="section-heading model-heading"),
        html.Div([
            html.Div([html.Span("ROC-AUC"), html.Strong(f"{metrics['roc_auc']:.3f}")]),
            html.Div([html.Span("Average precision"), html.Strong(f"{metrics['average_precision']:.3f}")]),
            html.Small("Full held-out set · historical metrics · unaffected by geography · September 2026"),
        ], className="model-summary"),
        html.Div([
            chart_card("Where model scores are concentrated", "Held-out association scores in 0.05-wide bands; not validated future claim probabilities.",
                       "risk-distribution", headline_id="risk-takeaway",
                       footer="Darker bins identify scores below 0.20 for description only; 0.20 is not a classification threshold."),
            chart_card("How scores relate to observed claims", "The same held-out score bands: observed HasClaim share versus mean model score.",
                       "risk-observed", footer="Hover for band size. Small groups can fluctuate; gaps mean no observations in a band."),
        ], className="chart-grid"),
        html.Div(id="risk-story", className="insight-strip", **{"aria-live": "polite"}),
    ]


def explorer_page(track, state="ALL", page=0):
    """Return one bounded page of aggregate rows from the dated snapshot."""
    if track == "risk":
        frame = table("risk", "segments").replace({"Không rõ": "Unknown"})
        frame = frame.sort_values(["observations", "state"], ascending=[False, True])
        headers = ["State", "Gender", "Age group", "Observations", "Exposure", "Premiums", "Claims", "Claim count", "HasClaim share"]
    else:
        frame = table("market", "monthly").sort_values(["month", "state"], ascending=[False, True])
        headers = ["Month", "State", "Premiums", "Claims", "Claims / premiums", "Observations"]
    if state and state != "ALL":
        frame = frame.loc[frame["state"] == state]
    total = len(frame)
    pages = max(1, (total + EXPLORER_PAGE_SIZE - 1) // EXPLORER_PAGE_SIZE)
    page = max(0, min(int(page or 0), pages - 1))
    rows = []
    for row in frame.iloc[page * EXPLORER_PAGE_SIZE:(page + 1) * EXPLORER_PAGE_SIZE].to_dict("records"):
        if track == "risk":
            share = ratio(row["has_claim"], row["observations"])
            rows.append([row["state"], row["gender"], row["age"], f"{row['observations']:,}",
                         f"{row['exposure']:,.2f}", f"{row['premium']:,.2f}", f"{row['claims']:,.2f}",
                         f"{row['claim_count']:,}", number(share, percent=True)])
        else:
            share = ratio(row["claims"], row["premium"])
            rows.append([row["month"][:7], row["state"], f"{row['premium']:,.2f}",
                         f"{row['claims']:,.2f}", number(share, percent=True), f"{row['observations']:,}"])
    return headers, rows, total, page, pages


def data_explorer():
    states = sorted(table("market", "monthly")["state"].unique())
    return html.Section([
        html.Div([html.Div([html.H2("Inspect the data behind the charts"),
                           html.P("Browse actual aggregate rows from the dated SQL export. Premiums, claims and exposure retain source units; shares are percentages.")]),
                  html.Span("DATA EXPLORER", className="small-badge")], className="chart-heading"),
        html.Div([
            dcc.RadioItems(id="data-track", value="market", options=[
                {"label": "SUSEP market", "value": "market"}, {"label": "Motor risk", "value": "risk"},
            ], className="segmented data-switch"),
            state_filter("data", states),
            html.Span(id="data-count", className="data-count"),
        ], className="data-controls"),
        dcc.Store(id="data-page", data=0),
        html.Div(id="data-table", className="table-scroll data-table", tabIndex=0, role="region",
                 **{"aria-label": "Paginated aggregate data"}),
        html.Div([html.Span(id="data-page-status", **{"aria-live": "polite"}),
                  html.Div([html.Button("Previous", id="data-prev", className="button"),
                            html.Button("Next", id="data-next", className="button")], className="data-actions")],
                 className="data-pagination"),
        html.Div("These are grouped snapshot records, not raw source rows or individual policies. Refresh the SQL export to update them.",
                 className="chart-footnote"),
    ], className="chart-card data-panel")


def platform_page():
    data = snapshot()
    perf, counts = pd.DataFrame(data["performance"]), data["counts"]
    matched = sum(counts[f"{p}_staging"] == counts[f"{p}_fact"] for p in ("market", "risk"))
    reductions = 100 * (1 - perf["after_reads"] / perf["before_reads"])
    chart = figure("SQL logical reads", "Logical reads · SQL page accesses", "")
    for col, name, color in [("before_reads", "Before index", CONTEXT), ("after_reads", "After index", TEAL)]:
        chart.add_bar(y=[f"Q{i + 1}" for i in range(len(perf))], x=perf[col], name=name, orientation="h", marker_color=color,
                      customdata=perf["workload"],
                      text=[f"{v:,}" for v in perf[col]], textposition="outside", cliponaxis=False,
                      hovertemplate="%{y} · %{customdata}<br>%{fullData.name}: %{x:,} logical reads<extra></extra>")
    chart.update_layout(barmode="group", bargap=.48, margin=dict(l=12, r=65, t=56, b=24))
    chart.update_xaxes(type="linear", range=[0, float(perf["before_reads"].max()) * 1.25], nticks=4,
                      showgrid=True, gridcolor=GRID)
    chart.update_yaxes(autorange="reversed", showgrid=False, ticklabelstandoff=12)
    return [
        page_header("PLATFORM ASSURANCE / ENGINEERING", "See the data behind the platform",
                    "Inspect warehouse aggregates, then weigh faster SQL reads against their storage cost.",
                    "EVIDENCE WINDOW", "Snapshot + historical benchmark", "SQL benchmark measured 24 Sep 2026"),
        html.Div([
            metric("Warehouse observations", number(counts["market_fact"] + counts["risk_fact"]), "Across two independent data tracks", symbol="database"),
            metric("Row-count reconciliation", f"{matched} / 2", "Staging and fact counts in this snapshot", symbol="check", tone="positive" if matched == 2 else "negative"),
            metric("Q1 logical reads saved", f"{reductions.iloc[0]:.2f}%", "Historical company / month workload", symbol="risk", tone="positive" if reductions.iloc[0] > 0 else "negative"),
            metric("Additional index storage", f"{perf['index_mb'].sum():,.2f} MB", "Two covering indexes · added write cost", symbol="database", tone="cost"),
        ], className="metrics"),
        data_explorer(),
        html.Section([
            html.Div([html.Div([html.H2("Fewer reads, with an explicit storage cost"),
                               html.P("SQL Server STATISTICS IO · warm cache · measured 24 September 2026")]),
                      html.Span("HISTORICAL BENCHMARK", className="small-badge")], className="chart-heading"),
            html.Div([graph(chart=chart), html.Div([
                html.Div([html.Span(f"Q{i + 1:02d}"), html.Strong(f"{value:.2f}%"),
                          html.P(f"fewer logical reads · {perf.iloc[i]['workload']}"),
                          html.Small(f"{perf.iloc[i]['before_reads']:,} → {perf.iloc[i]['after_reads']:,} pages")],
                         className="benchmark-stat") for i, value in enumerate(reductions)
            ], className="benchmark-summary")], className="benchmark-layout"),
            html.Div("Linear scale starts at zero. Short after-index bars reflect the measured reduction; labels show exact counts. This is not end-to-end dashboard speed.", className="chart-footnote"),
        ], className="chart-card benchmark-card"),
    ]


def navigation_label(symbol, title):
    return html.Span([icon(symbol), html.Strong(title)], className="nav-option")


app.layout = html.Div([
    html.A("Skip to content", href="#page-content", className="skip-link"),
    html.Aside([
        html.A([html.Span(icon("shield"), className="brand-mark"),
                html.Div([html.Strong("Insurance"), html.Span("INTELLIGENCE")])], href="/", className="brand"),
        html.Div("EXPLORE", className="nav-label"),
        html.Nav(dcc.RadioItems(id="section", value="market", options=[
            {"label": navigation_label("grid", "Market"), "value": "market"},
            {"label": navigation_label("risk", "Motor risk"), "value": "risk"},
            {"label": navigation_label("database", "Data"), "value": "platform"},
        ], className="nav-items"), **{"aria-label": "Analytics sections"}),
    ], className="sidebar"),
    html.Main([
        html.Header([html.Div([html.Span("Workspace"), html.Span("/", className="breadcrumb-divider"), html.Strong("Insurance analytics")], className="breadcrumb"),
                     html.Div(id="source-meta")], className="topbar"),
        html.Div(id="page-content"),
    ], className="workspace"),
], className="shell")


@app.callback(Output("page-content", "children"), Output("source-meta", "children"), Input("section", "value"))
def render_page(section):
    try:
        page = {"market": market_page, "risk": risk_page, "platform": platform_page}.get(section, market_page)()
        return html.Div(page, key=section, id=f"view-{section}"), provenance()
    except (OSError, ValueError, KeyError) as exc:
        return html.Div([html.H1("A data snapshot is needed"), html.P(str(exc)), html.Code("python pipeline/manage.py export")], className="snapshot-error"), ""


@app.callback(Output("data-page", "data"), Input("data-prev", "n_clicks"), Input("data-next", "n_clicks"),
              Input("data-track", "value"), Input("data-state", "value"), State("data-page", "data"))
def change_data_page(previous, following, track, state, page):
    if ctx.triggered_id in ("data-track", "data-state", None):
        return 0
    _, _, _, current, pages = explorer_page(track, state, page)
    return max(0, current - 1) if ctx.triggered_id == "data-prev" else min(pages - 1, current + 1)


@app.callback(Output("data-table", "children"), Output("data-count", "children"),
              Output("data-page-status", "children"), Output("data-prev", "disabled"),
              Output("data-next", "disabled"), Input("data-track", "value"),
              Input("data-state", "value"), Input("data-page", "data"))
def render_explorer(track, state, page):
    headers, rows, total, current, pages = explorer_page(track, state, page)
    if rows:
        content = html.Table([
            html.Thead(html.Tr([html.Th(label, scope="col", className="numeric" if label not in
                                       ("Month", "State", "Gender", "Age group") else "") for label in headers])),
            html.Tbody([html.Tr([html.Td(value, className="numeric" if headers[i] not in
                                        ("Month", "State", "Gender", "Age group") else "")
                                  for i, value in enumerate(row)]) for row in rows]),
        ])
    else:
        content = html.P("No aggregate rows match this state.", className="data-empty")
    first = current * EXPLORER_PAGE_SIZE + 1 if total else 0
    last = min((current + 1) * EXPLORER_PAGE_SIZE, total)
    return (content, f"{total:,} aggregate rows", f"Rows {first:,}–{last:,} · Page {current + 1} of {pages}",
            current == 0, current >= pages - 1)


@app.callback(Output("market-state", "value"), Output("market-years", "value"), Input("market-reset", "n_clicks"), prevent_initial_call=True)
def reset_market(clicks):
    years = table("market", "monthly")["month"].str[:4].astype(int)
    return "ALL", [int(years.min()), int(years.max())]


@app.callback(Output("risk-state", "value"), Input("risk-reset", "n_clicks"), prevent_initial_call=True)
def reset_risk(clicks):
    return "ALL"


def empty_figure(chart):
    chart.add_annotation(text="No observations for this selection", x=.5, y=.5, xref="paper", yref="paper", showarrow=False,
                         font=dict(color=MUTED, size=13))
    return chart


def product_label(value):
    source = snapshot()["market"]["product_names"].get(str(value), str(value))
    code = source.split(" - ", 1)[0]
    return f"{code} · {PRODUCTS.get(code, 'Product line ' + code)}"


def ranking_label(label, key):
    if key == "company":
        label = label.split("(", 1)[0].strip()
        for term in ("COMPANHIA DE SEGUROS GERAIS", "COMPANHIA DE SEGUROS", "E PREVIDÊNCIA", "SEGUROS", "SEGURADORA"):
            label = label.replace(term, "")
        label = re.sub(r"\s+S[./]?A[.]?\s*$", "", label)
        label = " ".join(label.split()).strip(" -/")
        return label if len(label) <= 22 else label[:21].rstrip() + "…"
    code = label.split(" · ", 1)[0]
    return PRODUCT_SHORT.get(code, PRODUCTS.get(code, "Line " + code))


@app.callback(Output("market-metrics", "children"), Output("market-trend", "figure"), Output("market-companies", "figure"),
              Output("market-products", "figure"), Output("market-takeaway", "children"), Output("market-story", "children"),
              Input("market-state", "value"), Input("market-years", "value"), Input("market-grain", "value"))
def update_market(state, years, grain="monthly"):
    monthly, companies, products = market_frames(state, years)
    premium, claims = monthly["premium"].sum(), monthly["claims"].sum()
    claim_ratio, observations = ratio(claims, premium), int(monthly["observations"].sum())
    comparison = latest_market_comparison(monthly, state)
    cards = [
        metric("Total premiums", number(premium), "Source units · selected period", symbol="premium", exact=f"{premium:,.2f}",
               comparison=market_change(comparison, "premium_change")),
        metric("Total claims", number(claims), "Source units · reported claims", symbol="claims", tone="cost", exact=f"{claims:,.2f}"),
        metric("Claims / premiums", number(claim_ratio, percent=True), "Ratio of totals within your selection", symbol="percent",
               comparison=market_change(comparison, "ratio_change_pp", lower_is_better=True)),
        metric("Market observations", number(observations), f"{years[0]}–{years[1]} · {state if state != 'ALL' else 'All states'}", exact=f"{observations:,}"),
    ]
    trend = monthly.assign(period=monthly["month"].str[:4] if grain == "annual" else monthly["month"])
    trend = trend.groupby("period", as_index=False)[["premium", "claims"]].sum()
    annual = grain == "annual"
    plot = figure("Market trend " + grain, "Year" if annual else "Month", "Billions · source units")
    for column, name, color in [("premium", "Premiums", BLUE), ("claims", "Claims", ORANGE)]:
        plot.add_scatter(x=trend["period"], y=trend[column] / 1e9, name=name, mode="lines+markers" if annual else "lines",
                         line=dict(color=color, width=2.6, dash="dash" if column == "claims" else "solid"), marker=dict(size=5),
                         customdata=["Jan–Jul only" if annual and str(p) == "2023" else "Reported period" for p in trend["period"]],
                         hovertemplate=f"%{{x}} · %{{customdata}}<br>{name}: %{{y:,.2f}}B source units<extra></extra>")
    plot.update_layout(showlegend=True, margin=dict(t=54))
    plot.update_yaxes(rangemode="tozero")
    plot.update_xaxes(type="category", nticks=8) if annual else plot.update_xaxes(type="date", tickformat="%Y", nticks=8)
    if monthly.empty:
        empty_figure(plot)
    ranks = []
    for frame, key, limit in [(companies, "company", 10), (products, "product", 8)]:
        ranked = frame.groupby(key, as_index=False)["premium"].sum().nlargest(limit, "premium").sort_values("premium")
        labels = [snapshot()["market"]["company_names"].get(str(v), str(v)) if key == "company" else product_label(v) for v in ranked[key]]
        short = [ranking_label(label, key) for label in labels]
        bars = figure("Ranking " + key, "Premiums (B)", "")
        # Technical IDs keep distinct bars when abbreviated source labels coincide.
        bars.add_bar(x=ranked["premium"] / 1e9, y=ranked[key].astype(str), orientation="h",
                     marker_color=[BLUE if i == len(ranked) - 1 else PALE_BLUE for i in range(len(ranked))],
                     customdata=list(zip(labels, [100 * v / premium if premium > 0 else None for v in ranked["premium"]])),
                     text=[f"{v / 1e9:,.1f}" for v in ranked["premium"]], textposition="outside", cliponaxis=False,
                     hovertemplate="%{customdata[0]}<br>Premiums: %{x:,.2f}B source units<br>%{customdata[1]:.1f}% of all selected premiums<extra></extra>")
        bars.update_yaxes(type="category", tickvals=ranked[key].astype(str), ticktext=short,
                          showgrid=False, ticklabelstandoff=18, tickfont=dict(size=11))
        bars.update_xaxes(showgrid=True, gridcolor=GRID, nticks=4, rangemode="tozero")
        bars.update_layout(margin=dict(l=8, r=38, t=22, b=26), hovermode="closest", bargap=.38)
        if ranked.empty:
            empty_figure(bars)
        ranks.append(bars)
    headline = (f"Claims account for {number(claim_ratio, percent=True)} of premium volume" if claim_ratio is not None
                else "Premiums and claims within your selection")
    top_company = companies.groupby("company")["premium"].sum().nlargest(10).sum()
    top_product = products.groupby("product")["premium"].sum().nlargest(8).sum()
    story = (f"The same premium base, two views: the top 10 insurers account for {number(ratio(top_company, premium), percent=True)} "
             f"and the top 8 product lines for {number(ratio(top_product, premium), percent=True)} of selected premiums. "
             "Use the trend to locate changes, then the rankings to see where volume is concentrated. These views do not identify causes."
             if observations else "No market observations match this selection.")
    return cards, plot, *ranks, headline if observations else "No market observations match this selection", story


@app.callback(Output("risk-metrics", "children"), Output("risk-distribution", "figure"), Output("risk-observed", "figure"),
              Output("risk-age", "figure"), Output("risk-gender", "figure"), Output("risk-takeaway", "children"),
              Output("risk-model-metric", "children"), Output("risk-story", "children"), Input("risk-state", "value"))
def update_risk(state):
    segments, scores = risk_frames(state)
    population, observations = int(scores["observations"].sum()), int(segments["observations"].sum())
    cards = [
        metric("Risk observations", number(observations), "Full filtered risk warehouse", exact=f"{observations:,}"),
        metric("Total exposure", number(segments["exposure"].sum()), "Exposure in source units", symbol="shield"),
        metric("Claims / exposure", number(ratio(segments["claim_count"].sum(), segments["exposure"].sum())), "Claim count divided by total exposure", symbol="percent", tone="cost"),
        metric("Mean model score", f"{scores['score_sum'].sum() / population:.3f}" if population else "—", f"{population:,} filtered held-out observations", symbol="risk"),
    ]
    scores = scores.assign(band=scores["band"].clip(upper=19))
    bands = scores.groupby("band")[["observations", "score_sum", "positives"]].sum().reindex(range(20), fill_value=0).reset_index()
    x = (bands["band"] + .5) / 20
    distribution = figure("Score distribution", "Model score", "Held-out observations")
    distribution.add_bar(x=x, y=bands["observations"], width=.05, marker_color=[SCORE if b < 4 else "#c9c2d9" for b in bands["band"]],
                         customdata=list(zip(bands["band"] / 20, (bands["band"] + 1) / 20)),
                         hovertemplate="Score band: %{customdata[0]:.2f}–%{customdata[1]:.2f}<br>Observations: %{y:,}<extra></extra>")
    distribution.update_xaxes(range=[0, 1], dtick=.2)
    distribution.update_layout(bargap=0, hovermode="closest")
    distribution.update_yaxes(rangemode="tozero")
    observed = figure("Observed claim share", "Model score band", "Share / score (%)")
    denominator = bands["observations"].replace(0, float("nan"))
    band_details = list(zip(bands["band"] / 20, (bands["band"] + 1) / 20, bands["observations"], bands["positives"]))
    for values, name, color, dash in [
        (100 * bands["positives"] / denominator, "Observed HasClaim", ORANGE, "solid"),
        (100 * bands["score_sum"] / denominator, "Mean model score", SCORE, "dash"),
    ]:
        observed.add_scatter(x=x, y=values, mode="lines+markers", name=name, customdata=band_details, connectgaps=False,
                             line=dict(color=color, width=2.3, dash=dash), marker=dict(size=5),
                             hovertemplate="Band: %{customdata[0]:.2f}–%{customdata[1]:.2f}<br>%{fullData.name}: %{y:.1f}%<br>Band size: %{customdata[2]:,}<br>Observed HasClaim: %{customdata[3]:,}<extra></extra>")
    observed.update_layout(margin=dict(t=70))
    observed.update_xaxes(range=[0, 1], dtick=.2)
    observed.update_yaxes(range=[0, 105], ticksuffix="%")
    age = segments.assign(age=segments["age"].replace({"Không rõ": "Unknown"}))
    age = age.groupby("age")[["observations", "has_claim"]].sum().reindex(["18-25", "26-35", "36-45", "46-55", ">55", "Unknown"]).dropna().reset_index()
    shares = 100 * age["has_claim"] / age["observations"]
    age_plot = figure("Driver age", "Source age group", "Observations with a claim (%)")
    age_plot.add_bar(x=age["age"], y=shares, marker_color=[CONTEXT if a == "Unknown" else ORANGE for a in age["age"]],
                     text=[f"{v:.1f}%" for v in shares], textposition="outside", cliponaxis=False,
                     customdata=list(zip(age["observations"], age["has_claim"])),
                     hovertemplate="%{x}<br>HasClaim: %{y:.1f}%<br>Observations: %{customdata[0]:,}<br>HasClaim count: %{customdata[1]:,}<extra></extra>")
    if observations:
        overall = 100 * segments["has_claim"].sum() / observations
        age_plot.add_hline(y=overall, line_dash="dot", line_color=MUTED)
        age_plot.add_annotation(text=f"Dotted line · selected population {overall:.1f}%", x=0, y=1.06,
                                xref="paper", yref="paper", xanchor="left", showarrow=False,
                                font=dict(size=10, color=MUTED))
        age_plot.update_layout(margin=dict(t=42))
    age_plot.update_yaxes(range=[0, max(10, float(shares.max()) * 1.2)] if not shares.empty else [0, 100])
    gender = segments.assign(gender=segments["gender"].replace({"Không rõ": "Unknown"}))
    gender = gender.groupby("gender", as_index=False)["observations"].sum().sort_values("observations")
    gender_plot = figure("Profile labels", "Observations", "")
    gender_plot.add_bar(x=gender["observations"], y=gender["gender"], orientation="h",
                        marker_color=CONTEXT, customdata=100 * gender["observations"] / observations if observations else [],
                        text=[number(v) for v in gender["observations"]], textposition="outside", cliponaxis=False,
                        hovertemplate="Source label: %{y}<br>Observations: %{x:,}<br>%{customdata:.1f}% of selected warehouse<extra></extra>")
    gender_plot.update_layout(margin=dict(r=65), bargap=.48)
    gender_plot.update_yaxes(showgrid=False, ticklabelstandoff=14)
    gender_plot.update_xaxes(showgrid=True, gridcolor=GRID, nticks=4, rangemode="tozero")
    for chart in (distribution, observed):
        if not population:
            empty_figure(chart)
    for chart in (age_plot, gender_plot):
        if not observations:
            empty_figure(chart)
    below = bands.loc[bands["band"] < 4, "observations"].sum()
    headline = f"{number(ratio(below, population), percent=True)} of held-out scores fall below 0.20" if population else "No held-out scores match this selection"
    selected = bands.loc[bands["band"] < 4]
    low_share = ratio(selected["positives"].sum(), selected["observations"].sum())
    selected = bands.loc[bands["band"] >= 10]
    high_share = ratio(selected["positives"].sum(), selected["observations"].sum())
    story = (f"In the same held-out sample, scores below 0.20 have {number(low_share, percent=True)} observed HasClaim "
             f"({below:,} observations); scores at or above 0.50 have {number(high_share, percent=True)} "
             f"({int(selected['observations'].sum()):,} observations). These are descriptive groups, not decision thresholds "
             "or validated future probabilities." if population else "No held-out observations match this geography.")
    return cards[:3], distribution, observed, age_plot, gender_plot, headline, cards[3], story


@app.callback(Output("market-download", "data"), Input("market-export", "n_clicks"), State("market-state", "value"), State("market-years", "value"), prevent_initial_call=True)
def download_market(clicks, state, years):
    return dcc.send_data_frame(market_frames(state, years)[0].to_csv, "market-summary.csv", index=False) if clicks else no_update


@app.callback(Output("risk-download", "data"), Input("risk-export", "n_clicks"), State("risk-state", "value"), prevent_initial_call=True)
def download_risk(clicks, state):
    if not clicks:
        return no_update
    return dcc.send_data_frame(risk_frames(state)[0].replace({"Không rõ": "Unknown"}).to_csv, "risk-summary.csv", index=False)


@server.get("/healthz")
def health():
    try:
        data = snapshot()
        return {"status": "ok", "data_mode": "warehouse_snapshot", "exported_at_utc": data["exported_at_utc"]}
    except (OSError, ValueError, KeyError):
        return {"status": "data_unavailable"}, 503


if __name__ == "__main__":
    app.run(host=os.getenv("DASH_HOST", "127.0.0.1"), port=int(os.getenv("DASH_PORT", "8050")), debug=False)
