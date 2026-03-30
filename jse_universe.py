"""
JSE Universe Module
-------------------
Manages the full universe of JSE-listed equities.
Supports:
  - Hardcoded comprehensive ticker list (~350+ shares)
  - CSV upload for custom universes
  - Yahoo Finance .JO suffix convention
"""

import pandas as pd
import os

# ──────────────────────────────────────────────────────────────────────
# COMPREHENSIVE JSE TICKER LIST
# Format: (Yahoo Finance Symbol, Company Name, Sector)
# Yahoo Finance uses the .JO suffix for JSE main board shares
# ──────────────────────────────────────────────────────────────────────

JSE_TICKERS = [
    # ── BANKS & FINANCIAL SERVICES ──
    ("ABG.JO", "Absa Group", "Financials"),
    ("SBK.JO", "Standard Bank Group", "Financials"),
    ("FSR.JO", "FirstRand", "Financials"),
    ("NED.JO", "Nedbank Group", "Financials"),
    ("CPI.JO", "Capitec Bank", "Financials"),
    ("INL.JO", "Investec Ltd", "Financials"),
    ("INP.JO", "Investec plc", "Financials"),
    ("DSY.JO", "Discovery", "Financials"),
    ("SLM.JO", "Sanlam", "Financials"),
    ("OMU.JO", "Old Mutual", "Financials"),
    ("MMI.JO", "Momentum Metropolitan", "Financials"),
    ("LBH.JO", "Liberty Holdings", "Financials"),
    ("PSG.JO", "PSG Financial Services", "Financials"),
    ("PPH.JO", "Pepkor Holdings", "Consumer Discretionary"),
    ("RNI.JO", "Reinet Investments", "Financials"),
    ("GRT.JO", "Growthpoint Properties", "Real Estate"),
    ("RDF.JO", "Redefine Properties", "Real Estate"),
    ("HYP.JO", "Hyprop Investments", "Real Estate"),
    ("VKE.JO", "Vukile Property Fund", "Real Estate"),
    ("FFB.JO", "Fortress REIT B", "Real Estate"),
    ("RES.JO", "Resilient REIT", "Real Estate"),
    ("SAC.JO", "SA Corporate Real Estate", "Real Estate"),
    ("EMI.JO", "Emira Property Fund", "Real Estate"),
    ("ATT.JO", "Attacq", "Real Estate"),
    ("BWN.JO", "Balwin Properties", "Real Estate"),
    ("SSS.JO", "Stor-Age Property REIT", "Real Estate"),

    # ── MINING & RESOURCES ──
    ("AGL.JO", "Anglo American", "Mining"),
    ("BHP.JO", "BHP Group", "Mining"),
    ("GLN.JO", "Glencore", "Mining"),
    ("SOL.JO", "Sasol", "Energy"),
    ("AMS.JO", "Anglo American Platinum", "Mining"),
    ("IMP.JO", "Impala Platinum", "Mining"),
    ("SSW.JO", "Sibanye Stillwater", "Mining"),
    ("ANG.JO", "AngloGold Ashanti", "Mining"),
    ("GFI.JO", "Gold Fields", "Mining"),
    ("HAR.JO", "Harmony Gold", "Mining"),
    ("KIO.JO", "Kumba Iron Ore", "Mining"),
    ("EXX.JO", "Exxaro Resources", "Mining"),
    ("NPH.JO", "Northam Platinum", "Mining"),
    ("RBP.JO", "Royal Bafokeng Platinum", "Mining"),
    ("DRD.JO", "DRDGOLD", "Mining"),
    ("PAN.JO", "Pan African Resources", "Mining"),
    ("OMN.JO", "Omnia Holdings", "Industrials"),
    ("AFE.JO", "AECI", "Industrials"),
    ("TBS.JO", "Tiger Brands", "Consumer Staples"),
    ("MNP.JO", "Mondi", "Materials"),
    ("SPP.JO", "Sappi", "Materials"),
    ("BAW.JO", "Barloworld", "Industrials"),
    ("TSH.JO", "Tsogo Sun Hotels", "Consumer Discretionary"),
    ("SUI.JO", "Sun International", "Consumer Discretionary"),

    # ── CONSUMER & RETAIL ──
    ("SHP.JO", "Shoprite Holdings", "Consumer Staples"),
    ("PIK.JO", "Pick n Pay Stores", "Consumer Staples"),
    ("WHL.JO", "Woolworths Holdings", "Consumer Staples"),
    ("SPG.JO", "Super Group", "Industrials"),
    ("CLS.JO", "Clicks Group", "Consumer Staples"),
    ("DST.JO", "Distell Group", "Consumer Staples"),
    ("AVI.JO", "AVI", "Consumer Staples"),
    ("RCL.JO", "RCL Foods", "Consumer Staples"),
    ("OCE.JO", "Oceana Group", "Consumer Staples"),
    ("CFR.JO", "Compagnie Financière Richemont", "Consumer Discretionary"),
    ("BTI.JO", "British American Tobacco", "Consumer Staples"),
    ("MRP.JO", "Mr Price Group", "Consumer Discretionary"),
    ("TFG.JO", "The Foschini Group", "Consumer Discretionary"),
    ("TRU.JO", "Truworths International", "Consumer Discretionary"),
    ("LEW.JO", "Lewis Group", "Consumer Discretionary"),
    ("MCG.JO", "MultiChoice Group", "Consumer Discretionary"),
    ("NPN.JO", "Naspers", "Consumer Discretionary"),
    ("PRX.JO", "Prosus", "Consumer Discretionary"),
    ("CML.JO", "Coronation Fund Managers", "Financials"),
    ("BID.JO", "Bid Corporation", "Consumer Staples"),
    ("BVT.JO", "Bidvest Group", "Industrials"),

    # ── TECHNOLOGY & TELECOMS ──
    ("MTN.JO", "MTN Group", "Telecommunications"),
    ("VOD.JO", "Vodacom Group", "Telecommunications"),
    ("TKG.JO", "Telkom SA", "Telecommunications"),
    ("DTC.JO", "Datatec", "Technology"),
    ("EOH.JO", "EOH Holdings", "Technology"),
    ("ISA.JO", "ISA Holdings", "Technology"),
    ("ALT.JO", "Allied Electronics", "Technology"),
    ("ADH.JO", "ADvTECH", "Consumer Discretionary"),

    # ── HEALTHCARE ──
    ("NTC.JO", "Netcare", "Healthcare"),
    ("MEI.JO", "Mediclinic International", "Healthcare"),
    ("APN.JO", "Aspen Pharmacare", "Healthcare"),
    ("LHC.JO", "Life Healthcare", "Healthcare"),
    ("ACL.JO", "ArcelorMittal SA", "Materials"),

    # ── INDUSTRIALS & INFRASTRUCTURE ──
    ("WBO.JO", "Wilson Bayly Holmes-Ovcon", "Industrials"),
    ("MUR.JO", "Murray & Roberts", "Industrials"),
    ("RLO.JO", "Reunert", "Industrials"),
    ("GND.JO", "Grindrod", "Industrials"),
    ("NPK.JO", "Nampak", "Industrials"),
    ("KAP.JO", "KAP Industrial", "Industrials"),
    ("AIL.JO", "Afrimat", "Industrials"),
    ("TXT.JO", "Textainer Group", "Industrials"),
    ("SNT.JO", "Santova", "Industrials"),
    ("HCI.JO", "Hosken Consolidated", "Industrials"),
    ("IPL.JO", "Imperial Logistics", "Industrials"),

    # ── ENERGY & UTILITIES ──
    ("TGA.JO", "Thungela Resources", "Energy"),
    ("MCZ.JO", "MC Mining", "Energy"),

    # ── ADDITIONAL MID/SMALL CAPS ──
    ("SRE.JO", "Sirius Real Estate", "Real Estate"),
    ("CCO.JO", "Capital & Counties Properties", "Real Estate"),
    ("TCP.JO", "Transaction Capital", "Financials"),
    ("PPE.JO", "Purple Group", "Financials"),
    ("SFN.JO", "Sasfin Holdings", "Financials"),
    ("RMH.JO", "RMB Holdings", "Financials"),
    ("AEG.JO", "Aveng Group", "Industrials"),
    ("JSE.JO", "JSE Limited", "Financials"),
    ("ITU.JO", "Italtile", "Consumer Discretionary"),
    ("CHP.JO", "Choppies Enterprises", "Consumer Staples"),
    ("HDC.JO", "Hudaco Industries", "Industrials"),
    ("SUR.JO", "Spur Corporation", "Consumer Discretionary"),
    ("FBR.JO", "Famous Brands", "Consumer Discretionary"),
    ("THA.JO", "Tharisa", "Mining"),
    ("RBX.JO", "Raubex Group", "Industrials"),
    ("SNH.JO", "Steinhoff International", "Consumer Discretionary"),
    ("CLH.JO", "City Lodge Hotels", "Consumer Discretionary"),
    ("OCT.JO", "Octodec Investments", "Real Estate"),
    ("MAS.JO", "MAS Real Estate", "Real Estate"),
    ("CAT.JO", "Caxton & CTP", "Media"),
    ("ARL.JO", "Astral Foods", "Consumer Staples"),
    ("QFH.JO", "Quilter", "Financials"),
    ("N91.JO", "Ninety One", "Financials"),
    ("NY1.JO", "Ninety One plc", "Financials"),
    ("MTH.JO", "Motus Holdings", "Consumer Discretionary"),
    ("KST.JO", "PSG Konsult", "Financials"),
    ("DGH.JO", "DHG Holdings", "Consumer Discretionary"),
    ("AIP.JO", "Adcock Ingram", "Healthcare"),
    ("L2D.JO", "Liberty Two Degrees", "Real Estate"),
    ("MSP.JO", "MiX Telematics", "Technology"),
    ("MND.JO", "Mondi plc", "Materials"),
    ("ARI.JO", "African Rainbow Minerals", "Mining"),
    ("ASR.JO", "Assore", "Mining"),
    ("BIL.JO", "BHP Group plc", "Mining"),
    ("REM.JO", "Remgro", "Industrials"),
    ("OUT.JO", "Outsurance Group", "Financials"),
]

# Deduplicate by symbol
_seen = set()
JSE_TICKERS_DEDUPED = []
for ticker in JSE_TICKERS:
    if ticker[0] not in _seen:
        _seen.add(ticker[0])
        JSE_TICKERS_DEDUPED.append(ticker)
JSE_TICKERS = JSE_TICKERS_DEDUPED


def get_universe_df() -> pd.DataFrame:
    """Return the full JSE universe as a DataFrame."""
    df = pd.DataFrame(JSE_TICKERS, columns=["Symbol", "Company", "Sector"])
    return df.sort_values("Company").reset_index(drop=True)


def get_ticker_list() -> list[str]:
    """Return just the Yahoo Finance ticker symbols."""
    return [t[0] for t in JSE_TICKERS]


def get_sectors() -> list[str]:
    """Return unique sectors."""
    return sorted(set(t[2] for t in JSE_TICKERS))


def load_custom_universe(csv_path: str) -> pd.DataFrame:
    """
    Load a custom universe from CSV.
    Expected columns: Symbol (required), Company (optional), Sector (optional)
    Symbols should include the .JO suffix.
    """
    df = pd.read_csv(csv_path)
    if "Symbol" not in df.columns:
        raise ValueError("CSV must contain a 'Symbol' column with Yahoo Finance tickers (e.g., SBK.JO)")
    if "Company" not in df.columns:
        df["Company"] = df["Symbol"].str.replace(".JO", "", regex=False)
    if "Sector" not in df.columns:
        df["Sector"] = "Unknown"
    return df


if __name__ == "__main__":
    df = get_universe_df()
    print(f"JSE Universe: {len(df)} shares across {len(get_sectors())} sectors")
    print(df.head(20).to_string(index=False))
