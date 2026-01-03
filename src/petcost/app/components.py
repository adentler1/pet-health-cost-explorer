"""Reusable Streamlit components for Pet Health Cost Explorer."""

from typing import Optional

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from petcost.db import get_db


def render_breed_selector(
    species: str,
    key: str = "breed_selector",
) -> Optional[str]:
    """
    Render a breed selector dropdown.

    Args:
        species: Species to filter breeds by
        key: Unique key for the widget

    Returns:
        Selected breed_id or None
    """
    db = get_db()
    breeds = db.query_df(
        "SELECT breed_id, breed_name FROM breeds WHERE species = ? ORDER BY breed_name",
        (species,),
    )

    if breeds.empty:
        st.warning(f"No {species} breeds found in database")
        return None

    breed_options = dict(zip(breeds["breed_name"], breeds["breed_id"]))
    selected_name = st.selectbox(
        "Select Breed",
        options=list(breed_options.keys()),
        key=key,
    )

    return breed_options.get(selected_name)


def render_life_expectancy_chart(
    df: pd.DataFrame,
    highlight_breed: Optional[str] = None,
) -> go.Figure:
    """
    Render a life expectancy comparison chart.

    Args:
        df: DataFrame with life expectancy data
        highlight_breed: Breed to highlight

    Returns:
        Plotly figure
    """
    if df.empty:
        fig = go.Figure()
        fig.add_annotation(text="No data available", showarrow=False)
        return fig

    # Sort by life expectancy
    df = df.sort_values("le_years", ascending=True)

    # Create color array for highlighting
    colors = ["#1f77b4"] * len(df)
    if highlight_breed and highlight_breed in df["breed_id"].values:
        idx = df[df["breed_id"] == highlight_breed].index[0]
        colors[df.index.get_loc(idx)] = "#ff7f0e"

    fig = go.Figure()

    # Add error bars for uncertainty
    if "le_low" in df.columns and "le_high" in df.columns:
        fig.add_trace(
            go.Bar(
                x=df["le_years"],
                y=df["breed_name"],
                orientation="h",
                marker_color=colors,
                error_x=dict(
                    type="data",
                    symmetric=False,
                    array=df["le_high"] - df["le_years"],
                    arrayminus=df["le_years"] - df["le_low"],
                ),
                hovertemplate="<b>%{y}</b><br>Life expectancy: %{x:.1f} years<extra></extra>",
            )
        )
    else:
        fig.add_trace(
            go.Bar(
                x=df["le_years"],
                y=df["breed_name"],
                orientation="h",
                marker_color=colors,
            )
        )

    fig.update_layout(
        title="Life Expectancy by Breed",
        xaxis_title="Life Expectancy (years)",
        yaxis_title="",
        height=max(400, len(df) * 25),
        showlegend=False,
    )

    return fig


def render_risk_profile_chart(conditions: list[dict]) -> go.Figure:
    """
    Render a health risk profile chart.

    Args:
        conditions: List of condition dictionaries

    Returns:
        Plotly figure
    """
    if not conditions:
        fig = go.Figure()
        fig.add_annotation(text="No condition data available", showarrow=False)
        return fig

    df = pd.DataFrame(conditions)

    # Color by risk level
    color_map = {
        "low": "#2ecc71",
        "moderate": "#f39c12",
        "high": "#e74c3c",
        "very_high": "#c0392b",
    }
    colors = [color_map.get(c.get("risk_level", "moderate"), "#95a5a6") for c in conditions]

    fig = go.Figure()

    fig.add_trace(
        go.Bar(
            x=[c.get("prevalence_percent", c.get("metric_value", 0) * 100) for c in conditions],
            y=[c.get("condition_name", "") for c in conditions],
            orientation="h",
            marker_color=colors,
            hovertemplate="<b>%{y}</b><br>Prevalence: %{x:.1f}%<extra></extra>",
        )
    )

    fig.update_layout(
        title="Top Health Conditions by Prevalence",
        xaxis_title="Prevalence (%)",
        yaxis_title="",
        height=max(300, len(conditions) * 40),
        showlegend=False,
    )

    return fig


def render_cost_distribution_chart(
    annual_costs: Optional[dict],
    lifetime_costs: Optional[dict],
    currency: str = "GBP",
) -> go.Figure:
    """
    Render a cost distribution chart.

    Args:
        annual_costs: Dictionary with annual cost percentiles
        lifetime_costs: Dictionary with lifetime cost percentiles
        currency: Currency symbol

    Returns:
        Plotly figure
    """
    fig = go.Figure()

    currency_symbol = {"GBP": "£", "USD": "$", "EUR": "€"}.get(currency, currency)

    if annual_costs:
        fig.add_trace(
            go.Bar(
                name="Annual (Typical Year)",
                x=["P10 (Low)", "P50 (Median)", "P90 (High)"],
                y=[annual_costs.get("p10", 0), annual_costs.get("p50", 0), annual_costs.get("p90", 0)],
                marker_color="#3498db",
                text=[
                    f"{currency_symbol}{annual_costs.get('p10', 0):,.0f}",
                    f"{currency_symbol}{annual_costs.get('p50', 0):,.0f}",
                    f"{currency_symbol}{annual_costs.get('p90', 0):,.0f}",
                ],
                textposition="outside",
            )
        )

    if lifetime_costs:
        fig.add_trace(
            go.Bar(
                name="Lifetime Total",
                x=["P10 (Low)", "P50 (Median)", "P90 (High)"],
                y=[lifetime_costs.get("p10", 0), lifetime_costs.get("p50", 0), lifetime_costs.get("p90", 0)],
                marker_color="#e74c3c",
                text=[
                    f"{currency_symbol}{lifetime_costs.get('p10', 0):,.0f}",
                    f"{currency_symbol}{lifetime_costs.get('p50', 0):,.0f}",
                    f"{currency_symbol}{lifetime_costs.get('p90', 0):,.0f}",
                ],
                textposition="outside",
            )
        )

    fig.update_layout(
        title="Estimated Veterinary Cost Distribution",
        xaxis_title="Percentile",
        yaxis_title=f"Cost ({currency_symbol})",
        barmode="group",
        height=400,
    )

    return fig


def render_cost_comparison_chart(
    df: pd.DataFrame,
    metric: str = "p50",
    currency: str = "GBP",
) -> go.Figure:
    """
    Render a cost comparison chart across breeds.

    Args:
        df: DataFrame with cost data
        metric: Which percentile to display
        currency: Currency code

    Returns:
        Plotly figure
    """
    if df.empty:
        fig = go.Figure()
        fig.add_annotation(text="No cost data available", showarrow=False)
        return fig

    currency_symbol = {"GBP": "£", "USD": "$", "EUR": "€"}.get(currency, currency)

    # Sort by selected metric
    df = df.sort_values(metric, ascending=True)

    fig = go.Figure()

    fig.add_trace(
        go.Bar(
            x=df[metric],
            y=df["breed_name"],
            orientation="h",
            marker_color="#3498db",
            hovertemplate=f"<b>%{{y}}</b><br>Lifetime cost (P50): {currency_symbol}%{{x:,.0f}}<extra></extra>",
        )
    )

    fig.update_layout(
        title=f"Lifetime Cost Comparison (Median)",
        xaxis_title=f"Estimated Cost ({currency_symbol})",
        yaxis_title="",
        height=max(400, len(df) * 25),
        showlegend=False,
    )

    return fig


def render_synthetic_data_disclaimer() -> None:
    """Render a disclaimer about synthetic data."""
    st.warning(
        """
        **Estimated Data Notice**

        The cost figures shown are **estimates** based on:
        - Published veterinary fee schedules
        - Epidemiological prevalence data from academic studies
        - Monte Carlo simulation modeling

        Actual costs vary significantly based on location, individual pet health,
        treatment choices, and other factors. These estimates are for informational
        purposes only and should not be used for financial planning without
        consulting a veterinary professional.
        """
    )


def render_data_source_info() -> None:
    """Render information about data sources."""
    with st.expander("Data Sources & Methodology"):
        st.markdown(
            """
            ### Data Sources

            **Life Expectancy Data**
            - VetCompass (Royal Veterinary College) - UK population studies
            - Published in: Teng et al. 2022 Scientific Reports

            **Health Risk Data**
            - VetCompass breed-specific disorder prevalence studies
            - Agria Pet Insurance public breed profiles (Sweden)

            **Cost Data**
            - BVA Fee Survey published summaries
            - PDSA PAW Report annual surveys

            ### Methodology

            Costs are estimated using Monte Carlo simulation:

            1. **Condition Occurrence**: For each condition, we simulate whether
               it occurs based on breed-specific prevalence rates.

            2. **Cost Sampling**: When a condition occurs, we sample the treatment
               cost from a triangular distribution based on published fee ranges.

            3. **Aggregation**: Annual and lifetime costs are aggregated across
               10,000 simulation runs to generate percentile estimates.

            ### Limitations

            - Geographic focus is UK; other regions use adjusted estimates
            - Prevalence data may not reflect recent breed population changes
            - Cost data is based on 2024 UK veterinary fees
            - Individual variation is significant; these are population averages
            """
        )


def format_currency(amount: float, currency: str = "GBP") -> str:
    """Format a currency amount for display."""
    symbols = {"GBP": "£", "USD": "$", "EUR": "€", "SEK": "kr"}
    symbol = symbols.get(currency, currency + " ")
    return f"{symbol}{amount:,.0f}"


def render_metric_card(
    title: str,
    value: str,
    subtitle: Optional[str] = None,
    delta: Optional[str] = None,
) -> None:
    """Render a metric card."""
    col1, col2 = st.columns([3, 1])
    with col1:
        st.metric(label=title, value=value, delta=delta)
        if subtitle:
            st.caption(subtitle)
