# Genesee County Jurisdictions List
# This module contains all jurisdictions within Genesee County, Michigan

GENESEE_COUNTY_JURISDICTIONS = [
    # County and State Law Enforcement
    "Genesee County Sheriff's Office",
    "Michigan State Police - Flint Post",
    
    # City Police Departments
    "Burton Police Department", 
    "Clio Police Department",
    "Davison Police Department",
    "Fenton Police Department",
    "Flint Police Department",
    "Flushing Police Department",
    "Grand Blanc Police Department",
    "Linden Police Department",
    "Mount Morris Police Department",
    "Swartz Creek Police Department",
    
    # Township Police Departments
    "Davison Township Police Department",
    "Fenton Township Police Department",
    "Flint Township Police Department",
    "Flushing Township Police Department",
    "Genesee Township Police Department",
    "Grand Blanc Township Police Department",
    "Mount Morris Township Police Department",
    "Mundy Township Police Department",
    "Richfield Township Police Department",
    
    # Metro Stations
    "Metro Station - Swartz Creek",
    "Metro Station - Flint",
    
    # Other
    "Out of County",
    "Unknown"
]

def get_jurisdiction_list():
    """Return the complete list of Genesee County jurisdictions"""
    return GENESEE_COUNTY_JURISDICTIONS.copy()

def get_jurisdiction_options():
    """Return jurisdictions formatted for HTML select options"""
    options = []
    for jurisdiction in GENESEE_COUNTY_JURISDICTIONS:
        options.append({'value': jurisdiction, 'text': jurisdiction})
    return options

def is_valid_jurisdiction(jurisdiction_name):
    """Check if a jurisdiction name is valid for Genesee County"""
    return jurisdiction_name in GENESEE_COUNTY_JURISDICTIONS

def get_law_enforcement_jurisdictions():
    """Return only law enforcement agencies"""
    return [j for j in GENESEE_COUNTY_JURISDICTIONS if 'Police' in j or 'Sheriff' in j or 'State Police' in j]

def get_municipal_jurisdictions():
    """Return cities, townships, and villages"""
    return [j for j in GENESEE_COUNTY_JURISDICTIONS if 
            j.startswith('City of') or j.endswith('Township') or j.startswith('Village of')]
