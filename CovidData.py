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
#     cols = np.delete(cols, np.where(cols == 'fips'))
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