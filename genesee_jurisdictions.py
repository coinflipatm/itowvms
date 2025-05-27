# Genesee County Jurisdictions List
# This module contains all jurisdictions within Genesee County, Michigan

GENESEE_COUNTY_JURISDICTIONS = [
    # Cities
    "City of Burton",
    "City of Clio", 
    "City of Davison",
    "City of Fenton",
    "City of Flint",
    "City of Flushing",
    "City of Grand Blanc",
    "City of Linden",
    "City of Mount Morris",
    "City of Swartz Creek",
    
    # Townships
    "Argentine Township",
    "Atlas Township", 
    "Clayton Township",
    "Davison Township",
    "Fenton Township",
    "Flint Township",
    "Flushing Township", 
    "Forest Township",
    "Genesee Township",
    "Grand Blanc Township",
    "Montrose Township",
    "Mount Morris Township",
    "Mundy Township",
    "Richfield Township",
    "Thetford Township",
    "Vienna Township",
    
    # Villages
    "Village of Gaines",
    "Village of Goodrich",
    "Village of Otisville",
    
    # Law Enforcement Agencies
    "Genesee County Sheriff's Office",
    "Michigan State Police - Flint Post",
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
    
    # Special Districts/Authorities
    "Genesee County Parks & Recreation",
    "Bishop International Airport Authority",
    "University of Michigan - Flint Public Safety",
    "Kettering University Public Safety",
    "Mott Community College Public Safety",
    
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
