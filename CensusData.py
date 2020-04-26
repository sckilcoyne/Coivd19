import requests
import pandas as pd

# https://www.census.gov/data/developers/data-sets/popest-popproj/popest.html
# https://atcoordinates.info/2019/09/24/examples-of-using-the-census-bureaus-api-with-python/

def StateData ():
    
    # API for population data
    popAPI = 'api.census.gov/data/2019/pep/population'
    
    # API inputs
    popAPIData = 'POP'
    popAPIpredicate = 'state'
    popAPIpredicateValue = '*'
    
    # API call
    callPopAPI = 'https://' + popAPI + '?get=' + popAPIData + '&for=' + popAPIpredicate + ':' + popAPIpredicateValue
    print(callPopAPI)
    censusPopRaw = requests.get(callPopAPI)
    print('Population data API call result: ' + str(censusPopRaw.status_code) + ' ' + censusPopRaw.reason)
    
    # Pop data cleanup
    censusPop = censusPopRaw.json()
    dfPop = pd.DataFrame(censusPop[1:], columns=censusPop[0])
    dfPop = dfPop.set_index('state')
    dfPop.index.names = ['FIPS']
    # dfPop.head(5)

    # API for State names and fips
    callNamesAPI = 'https://api.census.gov/data/2010/dec/sf1?get=NAME&for=state:*'
    
    print(callNamesAPI)
    censusNamesRaw = requests.get(callNamesAPI)
    print('State name API call result: ' + str(censusNamesRaw.status_code) + ' ' + censusNamesRaw.reason)
    censusNames = censusNamesRaw.json()
    dfStateData = pd.DataFrame(censusNames[1:], columns=['State', 'FIPS'])
    dfStateData = dfStateData.set_index('FIPS')
    # dfStateData.head(5)

    dfStateData['Population'] = dfPop['POP']
#     dfStateData.head(5)

    return dfStateData

def CountyData():
    print('Not Implemented Yet')
    