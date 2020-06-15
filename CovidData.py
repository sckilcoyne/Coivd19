import pandas as pd
import numpy as np

dataSources = dict()
dataSources['NYT - States'] = {'Abbreviation': 'NYT',
                             'API': 'https://raw.githubusercontent.com/nytimes/covid-19-data/master/us-states.csv'}
# dataSources['NYT - Counties'] = {'Abbreviation': 'NYT',
#                                'API': 'https://raw.githubusercontent.com/nytimes/covid-19-data/master/us-counties.csv'}
dataSources['Covid Tracking Project'] = {'Abbreviation': 'CTP',
                                         'API': 'https://covidtracking.com/api/v1/states/daily.csv'}


# Download Coivid Data from source APIs
def get_data(source):  
    Raw = pd.read_csv(dataSources[source]['API'],parse_dates=[0])
    print(dataSources[source]['API'])
        
    return Raw
    
# Reorganize Downloaded Covid Data
def clean_data(dfRaw):
    cols = dfRaw.columns.values
    commonCols = ['date', 'fips']
    removeCols = ['state', 'total','hash','posNeg']
    
    #  Move fips to second column
    removeFIPS = np.add(np.where(cols == 'fips'), 1)
    cols = np.insert(cols,1,'fips')
    cols = np.delete(cols, removeFIPS)
    dfClean = dfRaw[cols]
    
    # Delete unused columns
    dfClean = dfClean.drop(removeCols, axis = 1, errors = 'ignore')

    # Convert fips to str
    dfClean['fips'] = dfClean['fips'].apply(str)
    
    # Create multi-index
    dfClean = dfClean.set_index(['fips','date'])
    dfClean = dfClean.sort_index()
    
    return dfClean

# Run all operations
def combine_data():
    for source in dataSources:
        data = get_data(source)
        data = clean_data(data)
        cols = data.columns.values + '(' + dataSources[source]['Abbreviation'] + ')'
        data.columns = cols
        
        try:
            dfCombined = pd.merge(dfCombined, data, how ='outer', right_index=True, left_index=True)
        except: # solves problem with merging without matching index values
            dfCombined = data
        
    return dfCombined

def cdc_death_data(dfStateData, debug = False):
#     debug = False
    
    # https://data.cdc.gov/NCHS/Weekly-Counts-of-Deaths-by-State-and-Select-Causes/3yf8-kanr
    weekDeath1418 = 'https://data.cdc.gov/resource/3yf8-kanr.json'
    # https://data.cdc.gov/NCHS/Weekly-Counts-of-Deaths-by-State-and-Select-Causes/muzy-jte6
    weekDeath1920 = 'https://data.cdc.gov/resource/muzy-jte6.json'
    # https://data.cdc.gov/NCHS/Provisional-Death-Counts-for-Coronavirus-Disease-C/pj7m-y5uh
#     covidDeath = 'https://data.cdc.gov/resource/pj7m-y5uh.json'

    print('Starting download CDC weekely death data...')
    cols = ['jurisdiction_of_occurrence', 'mmwryear', 'mmwrweek', 'weekendingdate', 'allcause']

    dfCDCdeaths = pd.DataFrame(columns = cols)
    for state in dfStateData['State']:
        if debug: print(state) 
        
        # Ignore USA
        if state == 'USA': continue
        
        # From 2014 to 2018
        weeklyDeaths = pd.read_json(weekDeath1418 + '?jurisdiction_of_occurrence=' + state.replace(' ','%20'))
        dfCDCdeaths = dfCDCdeaths.append(weeklyDeaths[cols])
        if debug: print(dfCDCdeaths.tail(5)) 
        
        # From 2019 to 2020
        weeklyDeathsNew = pd.read_json(weekDeath1920 + '?jurisdiction_of_occurrence=' + state.replace(' ','%20'))
        colRename = {'all_cause': 'allcause', 'week_ending_date': 'weekendingdate'} # CDC Changed column names on me
        weeklyDeathsNew.rename(columns = colRename, inplace = True)
        dfCDCdeaths = dfCDCdeaths.append(weeklyDeathsNew[cols])
        if debug: print(dfCDCdeaths.tail(5)) 

    colRename = {'jurisdiction_of_occurrence': 'state', 'mmwryear': 'year', 'mmwrweek': 'week'}
    dfCDCdeaths.rename(columns = colRename, inplace = True)

    for state, group in dfCDCdeaths.groupby('state'):
        dfCDCdeaths.loc[dfCDCdeaths['state'] == state, 'FIPS'] = dfStateData.loc[dfStateData['State'] == state].index.values[0]
    
    print('Downloaded CDC weekly death data for every state from 2014-present.')
    
    return dfCDCdeaths

def mobility_data_apple(dfAppleRaw, state):

    # Get data for specific state, adjust for US
    if state == 'USA':
        appleStateDataRaw = dfAppleRaw[dfAppleRaw['region'] == 'United States'].T
        print('Collected Apple USA data')
    else:
        appleStateDataRaw = dfAppleRaw[dfAppleRaw['region'] == state].T
    # print(appleStateDataRaw)

    # Data header
    appleTransType = 'apple_' + appleStateDataRaw.iloc[2]
    # print(appleTransType)

    # Create formatted dataframe of state data
    dfAppleState = appleStateDataRaw.iloc[6:]
    dfAppleState.rename(columns = appleTransType, inplace = True)
    dfAppleState.index.names = ['date']
    dfAppleState = dfAppleState.assign(state=state).set_index('state', append = True)
    
#     print(dfAppleState.head(5))
    # Normalize to 0 instead of 100
    dfAppleState = dfAppleState - 100

    # print(dfAppleState.index)
    

    return dfAppleState

def mobility_data_google(dfGoogleRaw, state):
    # Filter data to just state level, adjust for country
    if state == 'USA':
        googleStateDataRaw = dfGoogleRaw[(dfGoogleRaw['country_region'] == 'United States') & (pd.isnull(dfGoogleRaw['sub_region_1']))]
        googleStateDataRaw['sub_region_1'] = 'USA'
#         print(googleStateDataRaw.head(5))
        print('Collected Google USA data')
    else:
        googleStateDataRaw = dfGoogleRaw[(dfGoogleRaw['sub_region_1'] == state) & (pd.isnull(dfGoogleRaw['sub_region_2']))]

    # Clean up data headers
    googleHeadersRaw = googleStateDataRaw.columns.values
    # print(googleHeadersRaw)
    trashString = '_percent_change_from_baseline'
    googleHeaders = [x.replace(trashString,'') for x in googleHeadersRaw]
    googleHeaders = [('google_' + x) for x in googleHeaders]
    # print(googleHeaders)

    # Create formatted dataframe of state data
    googleStateData = googleStateDataRaw
    googleStateData.columns = googleHeaders
    googleStateData.rename(columns = {'google_sub_region_1': 'state',
                                     'google_date': 'date'}, inplace = True)
    googleStateData = googleStateData.set_index(['date', 'state'])

    # Remove spurious columns
    dropCols = ['google_country_region_code', 'google_country_region', 'google_sub_region_2',
                'google_iso_3166_2_code', 'google_census_fips_code']
    googleStateData.drop(dropCols, axis = 1, errors = 'ignore', inplace = True)


    # headers = googleData.columns.values
    # headers = [('google_' + x) for x in headers]
    # googleData.columns = headers


    # print(googleData.head(5))
    # print(googleData.index)

    return googleStateData

def mobility_data(dfStateData):
#     Data sources
#     Google: https://www.google.com/covid19/mobility/  
#     Apple: https://www.apple.com/covid19/mobility

    debug = False
    # Downloaded mobility data csv files
    appleCSV = 'applemobilitytrends'
    googleCSV = 'Global_Mobility_Report'

    csvFolder = 'C:/Users/Scott/CloudStation/Drive/Jupyter/Coivd19/data/'

    appleCSV = csvFolder + appleCSV + '.csv'
    googleCSV = csvFolder + googleCSV + '.csv'

    # Read mobility data
    dfAppleRaw = pd.read_csv(appleCSV)
    dfGoogleRaw = pd.read_csv(googleCSV)    
    
    print('Imported Apple and Google Mobility Reports')
    
    # Create master mobility dataframe
    dfMobility = pd.DataFrame()
    
    # Add each state mobility reports
    for state in dfStateData['State']:
        if state == 'USA': print(state)
        # Get state mobility data
        dfAppleState = mobility_data_apple(dfAppleRaw, state)
        googleStateData = mobility_data_google(dfGoogleRaw, state)

        # Merge mobility data sources
        dfMobilityState = pd.merge(dfAppleState, googleStateData, how ='outer', right_index=True, left_index=True)

        # Add state to master mobility dataframe
        dfMobility = dfMobility.append(dfMobilityState)

    # Fix index order
    dfMobility = dfMobility.reorder_levels([1,0]) # state, date
    dfMobility = dfMobility.sort_index()

    # Set data to fractional
    if debug: print(dfMobility.tail(20))
    dfMobility = dfMobility / 100

    # Get mean and 7 day mean of mobility measures
    dfMobility['mean'] = dfMobility.mean(axis = 1, skipna = True)
    dfMobility['mean_rolling_7_day'] = dfMobility['mean'].rolling(window = 7, min_periods = 3, center = True).mean()

    print('Created combined mobility report')
    return dfMobility