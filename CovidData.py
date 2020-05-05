import pandas as pd
import numpy as np

dataSources = dict()
dataSources['NYT - States'] = {'Abbreviation': 'NYT',
                             'API': 'https://raw.githubusercontent.com/nytimes/covid-19-data/master/us-states.csv'}
# dataSources['NYT - Counties'] = {'Abbreviation': 'NYT',
#                                'API': 'https://raw.githubusercontent.com/nytimes/covid-19-data/master/us-counties.csv'}
dataSources['Covid Tracking Project'] = {'Abbreviation': 'CTP',
                                         'API': 'https://covidtracking.com/api/v1/states/daily.csv'}


# Download Data from sources
def get_data(source):  
    Raw = pd.read_csv(dataSources[source]['API'],parse_dates=[0])
    print(dataSources[source]['API'])
        
    return Raw
    
# Reorganize Downloaded Data
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
    dfClean = dfClean.drop(removeCols, axis=1, errors = 'ignore')

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

def cdc_death_data(dfStateData):
    
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
        # From 2014 to 2018
        weeklyDeaths = pd.read_json(weekDeath1418 + '?jurisdiction_of_occurrence=' + state.replace(' ','%20'))
        dfCDCdeaths = dfCDCdeaths.append(weeklyDeaths[cols])
        # From 2019 to 2020
        weeklyDeathsNew = pd.read_json(weekDeath1920 + '?jurisdiction_of_occurrence=' + state.replace(' ','%20'))
        dfCDCdeaths = dfCDCdeaths.append(weeklyDeathsNew[cols])
    #     print(state)

    colRename = {'jurisdiction_of_occurrence': 'state', 'mmwryear': 'year', 'mmwrweek': 'week'}
    dfCDCdeaths.rename(columns = colRename, inplace = True)

    for state, group in dfCDCdeaths.groupby('state'):
        dfCDCdeaths.loc[dfCDCdeaths['state'] == state, 'FIPS'] = dfStateData.loc[dfStateData['State'] == state].index.values[0]
    
    print('Downloaded CDC weekly death data for every state from 2014-present.')
    
    return dfCDCdeaths