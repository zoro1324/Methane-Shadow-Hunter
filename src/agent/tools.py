"""
LangChain Agent Tools for Methane Shadow Hunter.

Custom tools for facility lookup, emission data retrieval,
and regulatory context search.
"""

from typing import Optional


def facility_lookup(lat: float, lon: float, radius_km: float = 5.0) -> str:
    """
    Look up the nearest oil & gas facilities to a given location.
    
    Args:
        lat: Latitude of the emission source
        lon: Longitude of the emission source
        radius_km: Search radius in kilometers
    
    Returns:
        Formatted string with facility details
    """
    from src.data.infrastructure import InfrastructureDB

    db = InfrastructureDB()
    results = db.find_nearest(lat, lon, radius_km)

    if not results:
        return f"No facilities found within {radius_km}km of ({lat}, {lon})"

    lines = [f"Found {len(results)} facilities within {radius_km}km of ({lat:.4f}, {lon:.4f}):\n"]
    for fac, dist in results[:5]:  # Top 5
        lines.append(
            f"  • {fac.name}\n"
            f"    ID: {fac.facility_id} | Type: {fac.facility_type}\n"
            f"    Operator: {fac.operator} | State: {fac.state}\n"
            f"    Status: {fac.status} | Distance: {dist:.2f} km"
        )
    return "\n".join(lines)


def get_emission_data(plume_id: str, emission_rate: float, uncertainty: float,
                       distance_m: float, facility_name: str) -> str:
    """
    Get formatted emission analysis data for a detected plume.
    
    Args:
        plume_id: Plume identifier
        emission_rate: Emission rate in kg/hr
        uncertainty: Uncertainty in kg/hr
        distance_m: Pinpoint accuracy in meters
        facility_name: Name of the attributed facility
    """
    # Classify the emission
    if emission_rate > 500:
        classification = "SUPER-EMITTER (>500 kg/hr)"
        urgency = "IMMEDIATE ACTION REQUIRED"
    elif emission_rate > 100:
        classification = "Major Emitter (100-500 kg/hr)"
        urgency = "High Priority - Investigate within 48 hours"
    elif emission_rate > 25:
        classification = "Significant Emitter (25-100 kg/hr)"
        urgency = "Medium Priority - Schedule inspection"
    else:
        classification = "Minor Emitter (<25 kg/hr)"
        urgency = "Low Priority - Monitor"

    # Annual impact estimate
    annual_tonnes = emission_rate * 8760 / 1000  # tonnes/year
    co2_equivalent = annual_tonnes * 80  # CH4 is ~80x CO2 over 20 years

    return (
        f"=== EMISSION ANALYSIS: {plume_id} ===\n"
        f"Facility: {facility_name}\n"
        f"Classification: {classification}\n"
        f"Urgency: {urgency}\n\n"
        f"Emission Rate: {emission_rate:.2f} ± {uncertainty:.2f} kg/hr\n"
        f"Annual Estimate: {annual_tonnes:.1f} tonnes CH4/year\n"
        f"CO2 Equivalent (GWP-20): {co2_equivalent:.0f} tonnes CO2e/year\n"
        f"Pinpoint Accuracy: {distance_m:.0f} meters from facility\n"
    )


def search_regulations(country: str = "India", sector: str = "oil_gas") -> str:
    """
    Search for relevant methane emission regulations.
    
    Args:
        country: Country to search regulations for
        sector: Industry sector
    """
    # Built-in regulatory database for India
    regulations = {
        "India": {
            "oil_gas": [
                {
                    "regulation": "Environment Protection Act, 1986",
                    "authority": "Ministry of Environment, Forest and Climate Change (MoEFCC)",
                    "relevance": "Governs air pollution standards including fugitive emissions from industrial facilities",
                    "provision": "Section 3 empowers the central government to take measures for environmental protection",
                },
                {
                    "regulation": "Air (Prevention and Control of Pollution) Act, 1981",
                    "authority": "Central Pollution Control Board (CPCB)",
                    "relevance": "Regulates air emissions from industrial sources",
                    "provision": "Requires consent from State Pollution Control Board for operation",
                },
                {
                    "regulation": "National Action Plan on Climate Change (NAPCC)",
                    "authority": "Prime Minister's Council on Climate Change",
                    "relevance": "India's commitment to greenhouse gas reduction including methane",
                    "provision": "National Mission for Enhanced Energy Efficiency targets fugitive emission reduction",
                },
                {
                    "regulation": "Petroleum and Natural Gas Regulatory Board Act, 2006",
                    "authority": "PNGRB",
                    "relevance": "Regulates downstream petroleum and gas activities including safety and leakage prevention",
                    "provision": "Technical standards for pipeline integrity and leak detection",
                },
                {
                    "regulation": "India's Long-Term Climate Strategy (2070 Net Zero)",
                    "authority": "Government of India",
                    "relevance": "India's pledge to achieve net-zero by 2070; methane reduction is critical pathway",
                    "provision": "Focuses on reducing emissions from fossil fuel operations",
                },
                {
                    "regulation": "Global Methane Pledge (Non-signatory Observer)",
                    "authority": "International",
                    "relevance": "While India has not signed the Global Methane Pledge, it participates as an observer",
                    "provision": "Target: 30% methane reduction by 2030 from 2020 levels",
                },
            ]
        }
    }

    country_regs = regulations.get(country, regulations["India"])
    sector_regs = country_regs.get(sector, country_regs.get("oil_gas", []))

    lines = [f"=== REGULATORY FRAMEWORK: {country} - {sector.upper()} ===\n"]
    for reg in sector_regs:
        lines.append(
            f"📜 {reg['regulation']}\n"
            f"   Authority: {reg['authority']}\n"
            f"   Relevance: {reg['relevance']}\n"
            f"   Provision: {reg['provision']}\n"
        )

    return "\n".join(lines)
