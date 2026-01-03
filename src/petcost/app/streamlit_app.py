"""Main Streamlit dashboard for Pet Health Cost Explorer."""

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

from petcost.app.components import (
    format_currency,
    render_cost_comparison_chart,
    render_cost_distribution_chart,
    render_data_source_info,
    render_life_expectancy_chart,
    render_risk_profile_chart,
    render_synthetic_data_disclaimer,
)
from petcost.config import get_settings
from petcost.db import get_db
from petcost.features.life_expectancy import (
    compare_breed_to_species_average,
    get_breed_life_expectancy,
    get_life_expectancy_comparison,
    get_species_average_life_expectancy,
)
from petcost.features.risk_profiles import (
    get_breed_risk_summary,
    get_overall_breed_risk_score,
    get_top_conditions_by_breed,
)
from petcost.schemas import verify_schema


def check_database() -> bool:
    """Check if the database exists and is populated."""
    settings = get_settings()
    db_path = settings.database_path_absolute

    if not db_path.exists():
        return False

    if not verify_schema():
        return False

    db = get_db()
    breed_count = db.get_table_count("breeds")
    return breed_count > 0


def build_database_if_needed() -> bool:
    """Build the database if it doesn't exist. Returns True if successful."""
    if check_database():
        return True

    # Auto-build for cloud deployment
    try:
        from petcost.pipeline.build_db import build_database

        with st.spinner("Building database for first run... This may take a minute."):
            build_database(rebuild=True)
        return check_database()
    except Exception as e:
        st.error(f"Failed to build database: {e}")
        return False


def get_breeds_list(species: str) -> pd.DataFrame:
    """Get list of breeds for a species."""
    db = get_db()
    return db.query_df(
        "SELECT breed_id, breed_name FROM breeds WHERE species = ? ORDER BY breed_name",
        (species,),
    )


def get_cost_data(breed_id: str, country: str) -> tuple:
    """Get cost simulation data for a breed."""
    db = get_db()

    # Get annual costs (single year)
    annual = db.execute(
        """
        SELECT p10, p50, p90, mean, std, is_synthetic
        FROM simulated_costs
        WHERE breed_id = ? AND country = ? AND age_end - age_start = 1
        ORDER BY generated_at DESC LIMIT 1
        """,
        (breed_id, country),
    )

    # Get lifetime costs
    lifetime = db.execute(
        """
        SELECT p10, p50, p90, mean, std, is_synthetic, age_end
        FROM simulated_costs
        WHERE breed_id = ? AND country = ? AND age_end - age_start > 1
        ORDER BY generated_at DESC LIMIT 1
        """,
        (breed_id, country),
    )

    annual_dict = dict(annual[0]) if annual else None
    lifetime_dict = dict(lifetime[0]) if lifetime else None

    return annual_dict, lifetime_dict


def get_all_breeds_costs(species: str, country: str) -> pd.DataFrame:
    """Get lifetime costs for all breeds of a species."""
    db = get_db()

    return db.query_df(
        """
        SELECT
            sc.breed_id,
            b.breed_name,
            sc.p10,
            sc.p50,
            sc.p90,
            sc.mean
        FROM simulated_costs sc
        JOIN breeds b ON sc.breed_id = b.breed_id
        WHERE b.species = ?
          AND sc.country = ?
          AND sc.age_end - sc.age_start > 1
        ORDER BY sc.p50 DESC
        """,
        (species, country),
    )


def main() -> None:
    """Main application entry point."""
    st.set_page_config(
        page_title="Pet Health Cost Explorer",
        page_icon="🐾",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # Check and build database if needed
    if not build_database_if_needed():
        st.error(
            """
            **Database could not be initialized.**

            If running locally, try:

            ```bash
            ./scripts/run_pipeline.sh
            ```
            """
        )
        return

    settings = get_settings()

    # Sidebar
    st.sidebar.title("🐾 Pet Health Cost Explorer")
    st.sidebar.markdown("---")

    # Species selector
    species = st.sidebar.radio(
        "Select Species",
        options=["dog", "cat"],
        format_func=lambda x: "🐕 Dog" if x == "dog" else "🐱 Cat",
        key="species_selector",
    )

    # Breed selector
    breeds_df = get_breeds_list(species)
    if breeds_df.empty:
        st.sidebar.warning(f"No {species} breeds found")
        return

    breed_options = dict(zip(breeds_df["breed_name"], breeds_df["breed_id"]))
    selected_breed_name = st.sidebar.selectbox(
        "Select Breed",
        options=list(breed_options.keys()),
        key="breed_selector",
    )
    selected_breed_id = breed_options.get(selected_breed_name)

    # Country selector
    country = st.sidebar.selectbox(
        "Country/Region for Cost Estimates",
        options=["UK", "DE"],
        format_func=lambda x: {"UK": "🇬🇧 United Kingdom", "DE": "🇩🇪 Germany"}[x],
        key="country_selector",
        help="Cost estimates vary by country. Life expectancy and risk data are universal.",
    )

    # Optional filters
    st.sidebar.markdown("---")
    st.sidebar.subheader("Optional Filters")

    sex_filter = st.sidebar.selectbox(
        "Sex",
        options=["all", "male", "female"],
        format_func=lambda x: {"all": "All", "male": "Male ♂", "female": "Female ♀"}[x],
        key="sex_filter",
    )

    st.sidebar.markdown("---")
    render_data_source_info()

    # Main content
    st.title(f"Health Cost Explorer: {selected_breed_name}")

    # Key metrics row
    col1, col2, col3, col4 = st.columns(4)

    # Life expectancy
    le_data = get_breed_life_expectancy(selected_breed_id, sex_filter, country)
    if le_data:
        with col1:
            st.metric(
                label="Life Expectancy",
                value=f"{le_data['le_years']:.1f} years",
                help=f"Range: {le_data['le_low']:.1f} - {le_data['le_high']:.1f} years",
            )

        # Compare to species average
        comparison = compare_breed_to_species_average(selected_breed_id, country)
        if comparison:
            with col2:
                delta_str = f"{comparison['difference_years']:+.1f} years"
                st.metric(
                    label=f"vs {species.title()} Average",
                    value=f"{comparison['species_avg_le']:.1f} years",
                    delta=delta_str,
                    delta_color="normal",
                )

    # Risk score
    risk_score = get_overall_breed_risk_score(selected_breed_id)
    if risk_score:
        with col3:
            st.metric(
                label="Health Risk Score",
                value=f"{risk_score['risk_score']:.0f}/100",
                help=risk_score['risk_category'],
            )

    # Cost estimate
    annual_costs, lifetime_costs = get_cost_data(selected_breed_id, country)
    if lifetime_costs:
        with col4:
            st.metric(
                label="Est. Lifetime Cost (Median)",
                value=format_currency(lifetime_costs["p50"], "GBP"),
                help="Estimated total veterinary costs over lifetime",
            )

    # Tabs for detailed information
    tab1, tab2, tab3, tab4 = st.tabs([
        "📊 Life Expectancy",
        "⚠️ Health Risks",
        "💰 Cost Estimates",
        "📈 Breed Comparison",
    ])

    with tab1:
        st.subheader("Life Expectancy Analysis")

        if le_data:
            col1, col2 = st.columns([2, 1])

            with col1:
                # Life expectancy chart for all breeds
                le_comparison = get_life_expectancy_comparison(species, country, sex_filter)
                fig = render_life_expectancy_chart(le_comparison, selected_breed_id)
                st.plotly_chart(fig, use_container_width=True)

            with col2:
                st.markdown("### Key Statistics")
                st.markdown(f"**Median Life Expectancy:** {le_data['le_years']:.1f} years")
                st.markdown(f"**Range:** {le_data['le_low']:.1f} - {le_data['le_high']:.1f} years")
                st.markdown(f"**Uncertainty:** ±{le_data['uncertainty_range']/2:.1f} years")

                st.markdown("---")
                st.markdown(f"**Data Source:** {le_data['source']}")
                if le_data.get("citation"):
                    st.caption(le_data["citation"])

                # Species average
                species_avg = get_species_average_life_expectancy(species, country)
                if species_avg["avg_le"]:
                    st.markdown("---")
                    st.markdown(f"**{species.title()} Average:** {species_avg['avg_le']:.1f} years")
                    st.markdown(f"**Range across breeds:** {species_avg['min_le']:.1f} - {species_avg['max_le']:.1f} years")
        else:
            st.info("No life expectancy data available for this breed.")

    with tab2:
        st.subheader("Breed Health Risk Profile")

        # Get top conditions
        top_conditions = get_top_conditions_by_breed(selected_breed_id, limit=10)

        if top_conditions:
            col1, col2 = st.columns([2, 1])

            with col1:
                fig = render_risk_profile_chart(top_conditions)
                st.plotly_chart(fig, use_container_width=True)

            with col2:
                st.markdown("### Top Health Concerns")

                for i, condition in enumerate(top_conditions[:5], 1):
                    risk_emoji = {
                        "low": "🟢",
                        "moderate": "🟡",
                        "high": "🟠",
                        "very_high": "🔴",
                    }.get(condition.get("risk_level", "moderate"), "⚪")

                    prevalence = condition.get("prevalence_percent", condition.get("metric_value", 0) * 100)
                    st.markdown(
                        f"{i}. {risk_emoji} **{condition['condition_name']}** - {prevalence:.1f}%"
                    )

                st.markdown("---")
                st.caption("Prevalence indicates the percentage of this breed affected by each condition over their lifetime.")

            # Risk summary
            risk_summary = get_breed_risk_summary(selected_breed_id)
            if risk_summary and risk_summary["condition_count"] > 0:
                st.markdown("---")
                st.markdown("### Risk Category Breakdown")

                categories = risk_summary.get("categories", {})
                if categories:
                    cat_cols = st.columns(len(categories))
                    for i, (category, count) in enumerate(categories.items()):
                        with cat_cols[i]:
                            st.metric(category.title(), count)
        else:
            st.info("No health risk data available for this breed.")

    with tab3:
        st.subheader("Estimated Veterinary Costs")

        # Show disclaimer for synthetic data
        if annual_costs and annual_costs.get("is_synthetic"):
            render_synthetic_data_disclaimer()

        if annual_costs or lifetime_costs:
            col1, col2 = st.columns([2, 1])

            with col1:
                fig = render_cost_distribution_chart(annual_costs, lifetime_costs, "GBP")
                st.plotly_chart(fig, use_container_width=True)

            with col2:
                st.markdown("### Cost Breakdown")

                if annual_costs:
                    st.markdown("**Annual Costs (Typical Year)**")
                    st.markdown(f"- Low (P10): {format_currency(annual_costs['p10'], 'GBP')}")
                    st.markdown(f"- Median (P50): {format_currency(annual_costs['p50'], 'GBP')}")
                    st.markdown(f"- High (P90): {format_currency(annual_costs['p90'], 'GBP')}")

                if lifetime_costs:
                    st.markdown("---")
                    st.markdown("**Lifetime Costs**")
                    st.markdown(f"- Low (P10): {format_currency(lifetime_costs['p10'], 'GBP')}")
                    st.markdown(f"- Median (P50): {format_currency(lifetime_costs['p50'], 'GBP')}")
                    st.markdown(f"- High (P90): {format_currency(lifetime_costs['p90'], 'GBP')}")

                    if lifetime_costs.get("age_end"):
                        st.caption(f"Based on life expectancy of ~{lifetime_costs['age_end']} years")

                st.markdown("---")
                st.caption(
                    "P10/P50/P90 represent the 10th, 50th, and 90th percentiles. "
                    "50% of pets are expected to fall between P10 and P90."
                )
        else:
            st.info("No cost data available for this breed. Try running the pipeline to generate estimates.")

    with tab4:
        st.subheader(f"Comparison Across All {species.title()} Breeds")

        # Get all breeds data
        all_costs = get_all_breeds_costs(species, country)

        if not all_costs.empty:
            # Cost comparison chart
            fig = render_cost_comparison_chart(all_costs, "p50", "GBP")
            st.plotly_chart(fig, use_container_width=True)

            # Summary statistics
            st.markdown("---")
            st.markdown("### Summary Statistics")

            col1, col2, col3 = st.columns(3)

            with col1:
                avg_cost = all_costs["p50"].mean()
                st.metric("Average Lifetime Cost", format_currency(avg_cost, "GBP"))

            with col2:
                min_cost = all_costs["p50"].min()
                min_breed = all_costs.loc[all_costs["p50"].idxmin(), "breed_name"]
                st.metric("Lowest Cost Breed", format_currency(min_cost, "GBP"), help=min_breed)

            with col3:
                max_cost = all_costs["p50"].max()
                max_breed = all_costs.loc[all_costs["p50"].idxmax(), "breed_name"]
                st.metric("Highest Cost Breed", format_currency(max_cost, "GBP"), help=max_breed)

            # Show full table
            with st.expander("View Full Data Table"):
                display_df = all_costs.copy()
                display_df["p10"] = display_df["p10"].apply(lambda x: format_currency(x, "GBP"))
                display_df["p50"] = display_df["p50"].apply(lambda x: format_currency(x, "GBP"))
                display_df["p90"] = display_df["p90"].apply(lambda x: format_currency(x, "GBP"))
                display_df = display_df.rename(columns={
                    "breed_name": "Breed",
                    "p10": "Low (P10)",
                    "p50": "Median (P50)",
                    "p90": "High (P90)",
                })
                st.dataframe(display_df[["Breed", "Low (P10)", "Median (P50)", "High (P90)"]], use_container_width=True)

        else:
            st.info("No comparison data available. Run the pipeline to generate cost estimates.")

    # Footer
    st.markdown("---")
    st.caption(
        "Pet Health Cost Explorer | Data sources: VetCompass, PDSA PAW Report, BVA Fee Survey | "
        "All cost estimates are for informational purposes only."
    )


def run_app() -> None:
    """Entry point for running via package script."""
    main()


if __name__ == "__main__":
    main()
