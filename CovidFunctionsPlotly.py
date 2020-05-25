import pandas as pd
import numpy as np
# import matplotlib.pyplot as plt 
from datetime import datetime, timedelta

import matplotlib.ticker as mtick
from matplotlib.ticker import FormatStrFormatter
import plotly
import plotly.express as px
import plotly.graph_objects as go
import plotly.figure_factory as ff
import plotly.offline as pyo

figHeight = 600
figWidth = 800

def correlations(shiftSearch, dfCovid, fipsList):
    shiftHeadings = []
    shiftHeadings = shiftHeadings + ['Case_autocorr_' + str(i) for i in range(shiftSearch)]
    shiftHeadings = shiftHeadings + ['Case_autocorr_log_' + str(i) for i in range(shiftSearch)]
    shiftHeadings = shiftHeadings + ['Shift_' + str(i) for i in range(shiftSearch)]
    shiftHeadings = shiftHeadings + ['Shift_log_' + str(i) for i in range(shiftSearch)]

    dfShiftCor = pd.DataFrame(columns = shiftHeadings, index = fipsList)
    
    # For each state in the data
    for fips in fipsList:
#         fips = str(fips)
        # Cases and log of Cases for each state
        posCases = pd.DataFrame(dfCovid.loc[fips]['positive_cases'])
        posCases['positive_cases_log'] = np.log(posCases['positive_cases'])
        # Deaths and log of Deaths for each state
        deathsRaw = pd.DataFrame(dfCovid.loc[fips]['deaths']).reset_index()
        deathsRaw['deaths_log'] = np.log(deathsRaw['deaths'])

        # Correlations for every 'i' days before
        for i in range(shiftSearch):
            # Auto-correlation of cases
            caseAutocorr = posCases['positive_cases'].autocorr(lag = i)
            dfShiftCor.at[fips,'Case_autocorr_' + str(i)] = caseAutocorr

            # Auto-correlation of log of cases
            caseAutocorrLog = posCases['positive_cases_log'].autocorr(lag = i)
            dfShiftCor.at[fips,'Case_autocorr_log_' + str(i)] = caseAutocorrLog

            # Deaths correlated to cases from 'i' days beforehand
            deathsShifted = deathsRaw.copy()
            deathsShifted['date'] = deathsShifted['date'] - pd.Timedelta(days = i)
            deathsShifted = deathsShifted.set_index(['date'])

            corCaseDeath = pd.merge(posCases, deathsShifted, on = 'date', how ='outer')
            corDeath = corCaseDeath[['positive_cases','deaths']].corr().iloc[0::2,-1].mean() 
            corDeathLog = corCaseDeath[['positive_cases_log','deaths_log']].corr().iloc[0::2,-1].mean() 
            dfShiftCor.at[fips,'Shift_' + str(i)] = corDeath
            dfShiftCor.at[fips,'Shift_log_' + str(i)] = corDeathLog
            
    print('Completed ' + str(shiftSearch) + ' days of case-death correlations and auto-correlations.')
    return dfShiftCor

def state_plot(dfCovid, dfShiftCor, dfStateData, dfEvents, dfCDCdeaths, dfMobility, fips, plotDateRange):
    # Notable Events
    dfEventsAll = dfEvents.groupby('FIPS').get_group('All')
    if str(fips).zfill(2) in dfEvents.groupby('FIPS').groups.keys():
        dfEventsState = dfEventsAll.append(dfEvents.groupby('FIPS').get_group(str(fips).zfill(2)))
    else:
        dfEventsState = dfEventsAll    
    
    # Tracking Plots
    figTracking = tracking_plot(dfCovid, fips, plotDateRange, dfStateData)
    
    # R effective estimate plot
    figReffective = r_effective_plot(dfCovid, fips, plotDateRange)
    
    # Correlation Plot
    figCorrelation = correlation_plot(dfShiftCor, fips)
    
    # Daily Testing Plot
    figDailyTesting = daily_testing_plot(dfCovid, fips, plotDateRange)
    
    # Testing Growth Plot
    figTestingGrow = testing_growth_plot(dfCovid, fips, plotDateRange)
    
    # Percent Positive Plot
    figTestPercent = percent_poisitve_plot(dfCovid, fips, plotDateRange)
    
    # Resource Usage Plots
    figResource = resource_usage_plot(dfCovid, fips, plotDateRange)
    
    # CDC Death Data
    figCDCdeaths = cdc_deaths_plot(dfCDCdeaths, dfCovid, dfStateData, fips)
    
    # Mobility tracking Plot
    figMobility = mobility_plot(dfMobility, dfStateData, fips)
    
    # Add per capita axis
    perCapFig = [figDailyTesting, figTestingGrow]
    for fig in perCapFig:
        fig = per_capita_axis(fig, dfStateData, fips)
        
    # Add event markers
    for fig in [figTracking, figReffective, figMobility]:
        fig = event_markers(fig, dfEventsState)
        
    # Overall figure formatting     
    figList = [figTracking, figReffective, figMobility,
               figDailyTesting, figTestPercent, figTestingGrow,
               figCDCdeaths, figResource, figCorrelation]
    htmlFile = 'figs/Tracking Data ' + dfStateData.at[str(fips).zfill(2), 'State'] + '.html'
    figures_to_html(figList, htmlFile)

    
def tracking_plot(dfCovid, fips, plotDateRange, dfStateData):
    fig = go.Figure()
    dates = dfCovid.loc[fips].index
    pop = int(dfStateData.at[str(fips).zfill(2), 'Population'])
    capita = 10000

    titleBase = 'Tracking Data - '
    plotOptions = ['Cumulative', 'Cumulative per 10,000', 'Daily', 'Daily per 10,000']
    scalingFactor = [1, capita / pop, 1, capita / pop]
    diff = [False, False, True, True]
    sourceList = ['(NYT, CTP)', '(NYT)', '(CTP)']
    sourceMarker = ['circle', 'y-up', 'y-down']

    for i, plot in enumerate(plotOptions):
        optionalPlots = 0
        # Cases
        for s, source in enumerate(['positive_cases', 'cases(NYT)', 'positive(CTP)']):
            cases = dfCovid.loc[fips][source] * scalingFactor[i]
            if diff[i]:
                cases = cases.diff().rolling(7, min_periods = 1, center = True, win_type = 'triang').mean()
            if s < 1:
                mode = 'lines'
            else:
                mode = 'markers'
            fig.add_trace(go.Scatter(x = dates, y = cases,
                                     mode = mode,
                                     line_color = 'blue',
                                     marker_line_color = 'blue',
                                     marker_symbol = sourceMarker[s],
                                     marker_line_width = 1,
                                     name='Reported Cases ' + sourceList[s],
                                     visible = False))    
         # Deaths
        for s, source in enumerate(['deaths', 'deaths(NYT)', 'death(CTP)']):
            cases = dfCovid.loc[fips][source] * scalingFactor[i]
            if diff[i]:
                cases = cases.diff().rolling(7, min_periods = 1, center = True, win_type = 'triang').mean()
            if s < 1:
                mode = 'lines'
            else:
                mode = 'markers'
            fig.add_trace(go.Scatter(x = dates, y = cases,
                                     mode=mode,
                                     line_color = 'orange',
                                     marker_line_color = 'orange',
                                     marker_symbol = sourceMarker[s],
                                     marker_line_width = 1,
                                     name='Deaths ' + sourceList[s],
                                     visible = False)) 

        hospitalized = dfCovid.loc[fips]['hospitalizedCumulative(CTP)']
        inICU = dfCovid.loc[fips]['inIcuCumulative(CTP)']
        onVent = dfCovid.loc[fips]['onVentilatorCumulative(CTP)']
        recover = dfCovid.loc[fips]['recovered(CTP)']

        if hospitalized.sum() > 0:
            hospitalized = hospitalized * scalingFactor[i]
            if diff[i]:
                hospitalized = hospitalized.diff().rolling(7, min_periods = 1, center = True, win_type = 'triang').mean()
            fig.add_trace(go.Scatter(x = dates, y = hospitalized,
                                     mode='lines',
                                     name='Hospitalized (CTP)',
                                     visible = False)) 
            optionalPlots = optionalPlots + 1
        if inICU.sum() > 0:
            inICU = inICU * scalingFactor[i]
            if diff[i]:
                inICU = inICU.diff().rolling(7, min_periods = 1, center = True, win_type = 'triang').mean()
            fig.add_trace(go.Scatter(x = dates, y = inICU,
                                     mode='lines',
                                     name='ICU (CTP)',
                                     visible = False)) 
            optionalPlots = optionalPlots + 1
        if onVent.sum() > 0:
            onVent = onVent * scalingFactor[i]
            if diff[i]:
                onVent = onVent.diff().rolling(7, min_periods = 1, center = True, win_type = 'triang').mean()
            fig.add_trace(go.Scatter(x = dates, y = onVent,
                                     mode='lines',
                                     name='Ventilator (CTP)',
                                     visible = False))
            optionalPlots = optionalPlots + 1
        if recover.sum() > 0:
            recover = recover * scalingFactor[i]
            if diff[i]:
                recover = recover.diff().rolling(7, min_periods = 1, center = True, win_type = 'triang').mean()
            fig.add_trace(go.Scatter(x = dates, y = recover,
                                     mode='lines',
                                     name='Recovered (CTP)',
                                     visible = False))
            optionalPlots = optionalPlots + 1



    # Case Inflection Points 
    cases = dfCovid.loc[fips]['positive_cases'].copy()    
    inflections = inflection_points(cases)

    plotNames = [fig.data[i].name for i in range(len(fig.data))]
    indexPosList = []
    indexPos = 0
    while True:
        try:
            # Search for item in list from indexPos to the end of list
            indexPos = plotNames.index('Reported Cases (NYT, CTP)', indexPos)
            # Add the index position in list
            indexPosList.append(indexPos)
            indexPos += 1
        except ValueError as e:
            break

    xData = cases.index[inflections]
    for casePlots in indexPosList:
        yData = fig.data[casePlots].y[inflections]    
        fig.add_trace(go.Scatter(x = xData, y = yData,
                                 mode='markers',
                                 marker_line_color = 'red',
                                 marker_symbol = 'x-thin',
                                 marker_line_width=2,
                                 name='Case Inflection Points'))



    # Reported de-active  
    recoverPosList = []
    recoverPos = 0
    while True:
        try:
            # Search for item in list from indexPos to the end of list
            recoverPos = plotNames.index('Recovered (CTP)', recoverPos)
            # Add the index position in list
            recoverPosList.append(recoverPos)
            recoverPos += 1
        except ValueError as e:
            break

    deathPosList = []
    deathPos = 0
    while True:
        try:
            # Search for item in list from indexPos to the end of list
            deathPos = plotNames.index('Deaths (NYT, CTP)', deathPos)
            # Add the index position in list
            deathPosList.append(deathPos)
            deathPos += 1
        except ValueError as e:
            break

    for i in range(len(deathPosList)):
        deaths = fig.data[deathPosList[i]].y

        if len(recoverPosList) > 0:
            recovered = fig.data[recoverPosList[i]].y
            recovered[np.isnan(recovered)] = 0    
            knownNonActive = np.add(deaths, recovered)
        else:
            knownNonActive = deaths
        posLessDeadRecov = fig.data[indexPosList[i]].y - knownNonActive
        fig.add_trace(go.Scatter(x = fig.data[deathPosList[i]].x, y = posLessDeadRecov,
                                 mode='lines',
                                 name='Positive less Recovered and Dead'))

    # Estimated Active
    dates = fig.data[indexPosList[0]].x
    for casePlot in range(len(indexPosList)):
        cases = fig.data[indexPosList[casePlot]].y
        dfCase = pd.DataFrame({'date': dates, 'cases': cases})
        dfCase = dfCase.set_index(['date'])
        estActive = pd.DataFrame({'date': dates, 'cases': cases})
        estActive['date'] = estActive['date'] + pd.Timedelta(days = 14)
        estActive = estActive.set_index(['date'])
        estActive['est_active'] = dfCase['cases'] - estActive['cases']
        fig.add_trace(go.Scatter(x = estActive.index, y = estActive['est_active'],
                                 mode='lines',
                                 name='Estimated Active (14 day case life)',
                                line_color = 'green'))    

    # Plot Visibility
    listVis = []
    for i in range(4):
        plotVis = list(np.repeat([i == 0], 3)) * 2  + [i == 0] * optionalPlots # Cases, deaths, optional
        plotVis = plotVis + list(np.repeat([i == 1], 3)) * 2  + [i == 1] * optionalPlots
        plotVis = plotVis + list(np.repeat([i == 2], 3)) * 2  + [i == 2] * optionalPlots
        plotVis = plotVis + list(np.repeat([i == 3], 3)) * 2  + [i == 3] * optionalPlots
        plotVis = plotVis + [i == 0, i == 1, i == 2, i == 3] # Inflection Points
        plotVis = plotVis + [i == 0, i == 1, i == 2, i == 3] # Active
        plotVis = plotVis + [i == 0, i == 1, i == 2, i == 3] # Estimated Active
        listVis = listVis + [plotVis]
    plotVisibility =  listVis   

    # Fig formatting
    fig.update_layout(
        title = {
            'text': titleBase + plotOptions[0],
            'x': 0.5,
            'xanchor': 'center'},
        showlegend = True,
        legend_font_size = 10,
        margin=dict(l=20, r=20, t=30, b=20),
        height = figHeight,
        width = figWidth,
        hovermode = 'x unified',
        # Add Daily and Per Capita buttons
        updatemenus=[
            dict(
                type="buttons",
                direction="down",
                active=0,
                x=1.4,
                y=0.2,
                buttons=list([
                    dict(label=plotOptions[0],
                         method="update",
                         args=[{"visible": plotVisibility[0]},
                               {"title": titleBase + plotOptions[0]}]),
                    dict(label=plotOptions[1],
                         method="update",
                         args=[{"visible": plotVisibility[1]},
                               {"title": titleBase + plotOptions[1]}]),
                    dict(label=plotOptions[2],
                         method="update",
                         args=[{"visible": plotVisibility[2]},
                               {"title": titleBase + plotOptions[2]}]),
                    dict(label=plotOptions[3],
                         method="update",
                         args=[{"visible": plotVisibility[3]},
                               {"title": titleBase + plotOptions[3]}]),
                ]),
            ),
            # Add y scale button
            # https://community.plotly.com/t/set-linear-or-log-axes-from-button-or-drop-down-menu-python/34927/2
            dict(
                type = "buttons",
                direction = 'left',
                buttons=list([
                    dict(
                        args=[{"yaxis.type": "linear"}],
                        label="Linear Y",
                        method="relayout"),
                    dict(
                        args=[{"yaxis.type": "log"}],
                        label="Log Y",
                        method="relayout")
                    ]),
            pad={"r": 10, "t": 10},
            showactive = False,
            x = 0.2,
            xanchor = 'right',
            y = 1.1,
            yanchor = "bottom")],
           # Add range slider
           # https://github.com/plotly/plotly.py/issues/828
            xaxis=dict(
                range = plotDateRange,
                rangeselector=dict(
                    buttons=list([
                        dict(count=1,
                             label="1m",
                             step="month",
                             stepmode="backward"),
                        dict(count=2,
                             label="2m",
                             step="month",
                             stepmode="backward"),
                    ])
                ),
                rangeslider=dict(
                    visible=True,
                    range = plotDateRange),
                type="date"))

    for trace in range(len(fig.data)):
        fig.data[trace].update(visible = plotVisibility[0][trace])
    return fig
    
def r_effective_plot(dfCovid, fips, plotDateRange):
    fig = go.Figure()
    
    tObserved = [1, 3, 7]
    for T in tObserved:
        try:
            Reff = dfCovid.loc[fips]['positive_cases'] / dfCovid.loc[fips]['positive_cases'].shift(T)
        except ZeroDivisionError:
            Reff = float('nan')
        
        try:
            totalTests = dfCovid.loc[fips]['positive_cases'] + dfCovid.loc[fips]['negative(CTP)']
            newTestsScaling = totalTests / totalTests.shift(T)
            ReffScale = dfCovid.loc[fips]['positive_cases'] / (dfCovid.loc[fips]['positive_cases'].shift(T) * newTestsScaling)
        except ZeroDivisionError:
            ReffScale = float('nan')            
        
        fig.add_trace(go.Scatter(x = Reff.index, y = Reff,
                             mode='lines',
                             name= str(T) + ' day Observed R = ' + str(Reff[-1].round(2))))
        fig.add_trace(go.Scatter(x = ReffScale.index, y = ReffScale,
                             mode='lines',
                             name=str(T) + ' day Adjusted  R = ' + str(ReffScale[-1].round(2))))
    
    # Fig formatting
    fig.update_layout(
        title = {
            'text':'Estimated R',
            'x':0.5,
            'xanchor': 'center'},
        yaxis_type = "log",
        yaxis_range = [np.log10(0.6), np.log10(6)],
        showlegend = True,
        margin = dict(l=20, r=20, t=30, b=20),
        height = figHeight,
        width = figWidth,
        hovermode = 'x unified',
        # Add range slider
        # https://github.com/plotly/plotly.py/issues/828
        xaxis=dict(
            range = plotDateRange,
            rangeselector=dict(
                buttons=list([
                    dict(count = 1,
                         label = "1m",
                         step = "month",
                         stepmode = "backward"),
                    dict(count = 2,
                         label = "2m",
                         step = "month",
                         stepmode = "backward"),
#                     dict(step="all")
                ])
            ),
            rangeslider = dict(
                visible = True,
                range = plotDateRange),
            type = "date"))
    
    return fig
    
def correlation_plot(dfShiftCor, fips):
    caseDeathCor = dfShiftCor.loc[fips,dfShiftCor.columns.str.match('Shift_\d')]
    caseDeathCorLog = dfShiftCor.loc[fips,dfShiftCor.columns.str.match('Shift_log_')]
    caseAutoCor = dfShiftCor.loc[fips,dfShiftCor.columns.str.match('Case_autocorr_\d')]
    caseAutoCorLog = dfShiftCor.loc[fips,dfShiftCor.columns.str.match('Case_autocorr_log_')]
    
    shiftRange = int(dfShiftCor.columns[-1].split('_')[-1]) + 1
    
    fig = go.Figure()
    x_data = [*range(shiftRange)]
    fig.add_trace(go.Scatter(x = x_data, y = caseDeathCor,
                             mode = 'lines',
                             name = 'Case vs. Deaths Shifted, Raw'))
    fig.add_trace(go.Scatter(x = x_data, y = caseDeathCorLog,
                             mode = 'lines',
                             name = 'Case vs. Deaths Shifted, Log-Log'))
    fig.add_trace(go.Scatter(x = x_data, y = caseAutoCor,
                             mode = 'lines',
                             name = 'Case Autocorrelation, Raw',
                             visible ='legendonly'))
    fig.add_trace(go.Scatter(x = x_data, y = caseAutoCorLog,
                             mode = 'lines',
                             name = 'Case Autocorrelation, Log',
                             visible ='legendonly'))
        
    # Fig formatting
    fig.update_layout(
        title = {
            'text':'Cases related to X days later',
            'x':0.5,
            'xanchor': 'center'},
        yaxis_range = [0.7, 1],
        showlegend = True,
        legend_orientation = "h",
        margin=dict(l=20, r=20, t=30, b=20),
        height = figHeight,
        width = figWidth,
        hovermode = 'x unified')
#     fig.show()
    return fig
    
def daily_testing_plot(dfCovid, fips, plotDateRange):
    dailyTesting = dfCovid.loc[fips]['positive_cases'].diff() + dfCovid.loc[fips]['negative(CTP)'].diff()
    dates = dfCovid.loc[fips].index
    
    dailyMoving3 = dailyTesting.rolling(window=3).mean()
    dailyMoving7 = dailyTesting.rolling(window=7).mean()
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(x = dates, y = dailyTesting,
                             mode = 'markers',
                             name = 'Daily Testing'))
    fig.add_trace(go.Scatter(x = dates, y = dailyMoving3,
                             mode = 'lines',
                             name = 'Daily Testing (3 day)',
                             visible='legendonly'))
    fig.add_trace(go.Scatter(x = dates, y = dailyMoving7,
                             mode = 'lines',
                             name = 'Daily Testing (7 day)'))

    fig_ymin = min(dailyMoving3.min(), dailyMoving7.min(), 0) * 1.1
    fig_ymax = max(dailyMoving3.max(), dailyMoving7.max()) * 1.1
    
    # Fig formatting
    fig.update_layout(
        title = {
            'text':'Daily Testing',
            'x':0.5,
            'xanchor': 'center'},
        yaxis_range = [fig_ymin, fig_ymax],
        showlegend = True,
        margin=dict(l=20, r=20, t=30, b=20),
        height = figHeight,
        width = figWidth,
        hovermode = 'x unified',
        # Add range slider
        # https://github.com/plotly/plotly.py/issues/828
        xaxis=dict(
            range = plotDateRange,
            rangeselector=dict(
                buttons=list([
                    dict(count=1,
                         label="1m",
                         step="month",
                         stepmode="backward"),
                    dict(count=2,
                         label="2m",
                         step="month",
                         stepmode="backward"),
#                     dict(step="all")
                ])
            ),
            rangeslider=dict(
                visible=True,
                range = plotDateRange),
            type="date"))
#     fig.show()
    return fig
    
    
def testing_growth_plot(dfCovid, fips, plotDateRange):
    fig = go.Figure()
#     ax.axhline(y=0, color='dimgray', linewidth = 1)
    
    dailyTesting = dfCovid.loc[fips]['positive_cases'].diff() + dfCovid.loc[fips]['negative(CTP)'].diff()
    testingGrowth = dailyTesting.diff()
    dates = dfCovid.loc[fips].index
    
    growthMoving3 = testingGrowth.rolling(window=3).mean()
    growthMoving7 = testingGrowth.rolling(window=7).mean()
    
    fig.add_trace(go.Scatter(x = dates, y = testingGrowth,
                             mode = 'markers',
                             name = 'Testing Growth'))
    fig.add_trace(go.Scatter(x = dates, y = growthMoving3,
                             mode = 'lines',
                             name = 'Testing Growth (3 day)',
                             visible='legendonly'))
    fig.add_trace(go.Scatter(x = dates, y = growthMoving7,
                             mode = 'lines',
                             name = 'Testing Growth (7 day)'))
    
    fig_ymin = min(growthMoving3.min(), growthMoving7.min(), 0) * 1.1
    fig_ymax = max(growthMoving3.max(), growthMoving7.max()) * 1.1    
    
    # Fig formatting
    fig.update_layout(
        title = {
            'text':'Testing Growth',
            'x':0.5,
            'xanchor': 'center'},
        yaxis_range = [fig_ymin, fig_ymax],
        showlegend = True,
        margin=dict(l=20, r=20, t=30, b=20),
        height = figHeight,
        width = figWidth,
        hovermode = 'x unified',
        # Add range slider
        # https://github.com/plotly/plotly.py/issues/828
        xaxis=dict(
            range = plotDateRange,
            rangeselector=dict(
                buttons=list([
                    dict(count=1,
                         label="1m",
                         step="month",
                         stepmode="backward"),
                    dict(count=2,
                         label="2m",
                         step="month",
                         stepmode="backward"),
#                     dict(step="all")
                ])
            ),
            rangeslider=dict(
                visible=True,
                range = plotDateRange),
            type="date"))
                
#     fig.show()
    return fig
    
def percent_poisitve_plot(dfCovid, fips, plotDateRange):
    dates = dfCovid.loc[fips].index
    totalTests = dfCovid.loc[fips]['positive_cases'] + dfCovid.loc[fips]['negative(CTP)']
    percentPositive = dfCovid.loc[fips]['positive_cases'] / totalTests
    percentPositive3day = percentPositive.rolling(window=3).mean()
    percentPositive7day = percentPositive.rolling(window=7).mean()

    positiveIncrease = dfCovid.loc[fips]['positive_cases'].diff()
    percentPosNew = positiveIncrease / totalTests.diff()
    percentPosNew3day = percentPosNew.rolling(window=3).mean()
    percentPosNew7day = percentPosNew.rolling(window=7).mean()

    fig = go.Figure()
    fig.add_trace(go.Scatter(x = dates, y = percentPositive,
                             mode = 'markers',
                             name = '% Positive Total',
                             visible='legendonly'))
    fig.add_trace(go.Scatter(x = dates, y = percentPositive3day,
                             mode = 'lines',
                             name = '% Positive Total (3 day)',
                             visible='legendonly'))
    fig.add_trace(go.Scatter(x = dates, y = percentPositive7day,
                             mode = 'lines',
                             name = '% Positive Total (7 day)'))
    
    fig.add_trace(go.Scatter(x = dates, y = percentPosNew,
                             mode = 'markers',
                             name = 'Daily % Positive'))
    fig.add_trace(go.Scatter(x = dates, y = percentPosNew3day,
                             mode = 'lines',
                             name = 'Daily % Positive (3 day)',
                             visible='legendonly'))
    fig.add_trace(go.Scatter(x = dates, y = percentPosNew7day,
                             mode = 'lines',
                             name = 'Daily % Positive (7 day)'))
        
    # Fig formatting
    fig.update_layout(
        title = {
            'text':'Positive Test Results',
            'x':0.5,
            'xanchor': 'center'},
        yaxis_tickformat = '1%',
        yaxis_range = [0, 0.6],
        showlegend = True,
        margin=dict(l=20, r=20, t=30, b=20),
        height = figHeight,
        width = figWidth,
        hovermode = 'x unified',
        # Add range slider
        # https://github.com/plotly/plotly.py/issues/828
        xaxis=dict(
            range = plotDateRange,
            rangeselector=dict(
                buttons=list([
                    dict(count=1,
                         label="1m",
                         step="month",
                         stepmode="backward"),
                    dict(count=2,
                         label="2m",
                         step="month",
                         stepmode="backward"),
#                     dict(step="all")
                ])
            ),
            rangeslider=dict(
                visible=True,
                range = plotDateRange),
            type="date"))
#     fig.show()
    return fig
    
def resource_usage_plot(dfCovid, fips, plotDateRange):
    plots = False
    dates = dfCovid.loc[fips].index
    fig = go.Figure()
    if dfCovid.loc[fips]['hospitalizedCurrently(CTP)'].sum() > 0:  
        fig.add_trace(go.Scatter(x = dates, y = dfCovid.loc[fips]['hospitalizedCurrently(CTP)'],
                             mode = 'lines',
                             name = 'Hospitalized (CTP)'))
        plots = True
    if dfCovid.loc[fips]['inIcuCurrently(CTP)'].sum() > 0:    
        fig.add_trace(go.Scatter(x = dates, y = dfCovid.loc[fips]['inIcuCurrently(CTP)'],
                             mode = 'lines',
                             name = 'ICU (CTP)'))
        plots = True
    if dfCovid.loc[fips]['onVentilatorCurrently(CTP)'].sum() > 0:  
        fig.add_trace(go.Scatter(x = dates, y = dfCovid.loc[fips]['onVentilatorCurrently(CTP)'],
                             mode = 'lines',
                             name = 'On Ventilator (CTP)'))
        plots = True

    
    if plots:
        fig.update_layout(
            title = {
                'text':'Current Resource Usuage',
                'x':0.5,
                'xanchor': 'center'})
    else:
        fig.update_layout(
            title = {
                'text':'No data on Resource Usuage',
                'x':0.5,
                'xanchor': 'center'})
    
    # Fig formatting
    fig.update_layout(
        showlegend = True,
        margin=dict(l=20, r=20, t=30, b=20),
        height = figHeight,
        width = figWidth,
        hovermode = 'x unified',
        # Add y scale button
        # https://community.plotly.com/t/set-linear-or-log-axes-from-button-or-drop-down-menu-python/34927/2
        updatemenus=[dict(
            type = "buttons",
            direction = 'left',
            buttons=list([
                dict(
                    args=[{"yaxis.type": "linear"}],
                    label="Linear Y",
                    method="relayout"),
                dict(
                    args=[{"yaxis.type": "log"}],
                    label="Log Y",
                    method="relayout")
                ]),
        showactive=False,
        x=0.2,
        xanchor="left",
        y=1,
        yanchor="top")],
        # Add range slider
        # https://github.com/plotly/plotly.py/issues/828
        xaxis=dict(
            range = plotDateRange,
            rangeselector=dict(
                buttons=list([
                    dict(count=1,
                         label="1m",
                         step="month",
                         stepmode="backward"),
                    dict(count=2,
                         label="2m",
                         step="month",
                         stepmode="backward"),
#                     dict(step="all")
                ])
            ),
            rangeslider=dict(
                visible=True,
                range = plotDateRange),
            type="date"))
    

#     fig.show()
    return fig

def cdc_deaths_plot(dfCDCdeaths, dfCovid, dfStateData, fips):
    previousYears = list(range(2014,2020))
    thisYear = 2020
    
    stateCount = len(dfStateData['State']) + 1
    weekCount = dfCDCdeaths.week.max()
    weekRange = range(1, weekCount + 1)

    cols = ['New_Deaths', 'Median', 'Upper_Quartile', 'Lower_Quartile', 'Max', 'Min']
    dfCDCState = pd.DataFrame(columns = cols, index = list(weekRange))
    
    fipsFilter = dfCDCdeaths.FIPS == str(fips).zfill(2)
    prevYearFilter = dfCDCdeaths.year.isin(previousYears)
    thisYearFilter = dfCDCdeaths.year == thisYear
    for w in weekRange:
        weekFilter = dfCDCdeaths.week == w
        oldDeaths = dfCDCdeaths[fipsFilter & weekFilter & prevYearFilter ]['allcause']
        newDeaths = dfCDCdeaths[fipsFilter & weekFilter & thisYearFilter ]['allcause']

        dfCDCState.at[w, 'New_Deaths'] = newDeaths.mean() # gets out of list
        dfCDCState.at[w, 'Median'] = oldDeaths.median()
        dfCDCState.at[w, 'Upper_Quartile'] = oldDeaths.quantile(0.75)
        dfCDCState.at[w, 'Lower_Quartile'] = oldDeaths.quantile(0.25)
        dfCDCState.at[w, 'Max'] = oldDeaths.max()
        dfCDCState.at[w, 'Min'] = oldDeaths.min()

    maxDiff = dfCDCState['New_Deaths'] - dfCDCState['Max']
    maxExcess = np.nansum((maxDiff > 0) * maxDiff)

    upperDiff = dfCDCState['New_Deaths'] - dfCDCState['Upper_Quartile']
    upperExcess = np.nansum((upperDiff > 0) * upperDiff)

    medianDiff = dfCDCState['New_Deaths'] - dfCDCState['Median']
    medianExcess = np.nansum((medianDiff > 0) * medianDiff)
    
    # Get state covid death data
    # Daily death data multiplied by 7 to get rolling weekly death data
    covidDeaths = dfCovid.loc[(fips), 'deaths'].diff().rolling(window = 7, min_periods = 5).mean() * 7
    covidWeek = dfCovid.loc[(fips), 'week']
        
    
    fig = go.Figure()
    
    # Raw CDC Data
    fig.add_trace(go.Scatter(x = dfCDCState.index, y = dfCDCState['New_Deaths'], 
                             name = '2020 Deaths',
                             line_color = 'firebrick'))
    fig.add_trace(go.Scatter(x = dfCDCState.index, y = dfCDCState['Median'], 
                             name = 'Median',
                             line_color = 'royalblue'))
    fig.add_trace(go.Scatter(x = dfCDCState.index, y = dfCDCState['Upper_Quartile'], 
                             name = 'Upper Quartile',
                             line_color = 'orange', line_dash = 'dash'))
    fig.add_trace(go.Scatter(x = dfCDCState.index, y = dfCDCState['Lower_Quartile'], 
                             name = 'Lower Quartile',
                             line_color = 'orange', line_dash = 'dot',
                             visible = 'legendonly'))
    fig.add_trace(go.Scatter(x = dfCDCState.index, y = dfCDCState['Max'], 
                             name = 'Max',
                             line_color = 'green', line_dash = 'dash'))
    fig.add_trace(go.Scatter(x = dfCDCState.index, y = dfCDCState['Min'], 
                             name = 'Min',
                             line_color = 'green', line_dash = 'dot',
                             visible = 'legendonly'))
    
#     yMinRaw = dfCDCState.iloc[1:]['Min'].min() * 0.9
#     yMaxRaw = max(dfCDCState.iloc[1:]['Max'].max(), dfCDCState.iloc[1:]['New_Deaths'].max()) * 1.1
    visibleRaw = [True, True, True, 'legendonly', True, 'legendonly']
    hiddenRaw = [False] * len(visibleRaw)

    # Normalized Data
    norm2020 = dfCDCState['New_Deaths'] - dfCDCState['Median']
    normMax = dfCDCState['Max'] - dfCDCState['Median']
    normMin = dfCDCState['Min'] - dfCDCState['Median']
    normUpper = dfCDCState['Upper_Quartile'] - dfCDCState['Median']
    normLower = dfCDCState['Lower_Quartile'] - dfCDCState['Median']
    
    fig.add_trace(go.Scatter(x = dfCDCState.index, y = norm2020, 
                             name = '2020 Deaths',
                             line_color = 'firebrick',
                             visible = False))
    fig.add_trace(go.Scatter(x = covidWeek, y = covidDeaths, 
                             name = 'Covid Deaths',
                             line_color = 'purple',
                             visible = False))
    fig.add_trace(go.Scatter(x = dfCDCState.index, y = normUpper, 
                             name = 'Upper Quartile',
                             line_color = 'orange', line_dash = 'dash',
                             visible = False))
    fig.add_trace(go.Scatter(x = dfCDCState.index, y = normLower, 
                             name = 'Lower Quartile',
                             line_color = 'orange', line_dash = 'dot',
                             visible = False))
    fig.add_trace(go.Scatter(x = dfCDCState.index, y = normMax, 
                             name = 'Max',
                             line_color = 'green', line_dash = 'dash',
                             visible = False))
    fig.add_trace(go.Scatter(x = dfCDCState.index, y = normMin, 
                             name = 'Min',
                             line_color = 'green', line_dash = 'dot',
                             visible = False))
#     yMinNorm = min(norm2020.min(), 0) * 1.1
#     yMaxNorm = max(norm2020.max(), normMax.max()) * 1.1
    visibleNorm = [True, True, True, 'legendonly', True, 'legendonly']
    hiddenNorm = [False] * len(visibleNorm)
    
    plotVisibility = [visibleRaw + hiddenNorm, hiddenRaw + visibleNorm]
    annotationText = ('Note: CDC data may be up to 8 weeks delayed.' + '<br>' + '<br>' +
        'Where 2020 is greater than X' + '<br>' +
        '2020 - Max = ' + str(maxExcess) + '<br>' +
        '2020 - Upper Quartile = ' + str(upperExcess) +  '<br>' + 
        '2020 - Median = ' + str(medianExcess))
    
    fig.update_layout(title_text = 'All Cause Reported Deaths 2014-2019 vs. 2020',
                      height = figHeight,
                      width = figWidth,
                      hovermode = 'x unified',
#                       yaxis_range = [yMinRaw, yMaxRaw],
                      xaxis_title = 'Week in Year',
                      annotations = [dict(x = 1.3, y = 1.2,
                                          showarrow = False,
                                          text = annotationText,
                                          font_size = 10,
                                          align = 'left',
                                          xref = 'paper', yref = 'paper')],
                      updatemenus = [dict(
                          type = 'buttons',
                          direction = 'down',
                          x = 1.3,
                          y = 0.2,
                          buttons = list([
                              dict(label = 'Raw CDC Data',
                                   method = 'update',
                                   args = [{'visible': plotVisibility[0]},
                                           {'title': 'All Cause Reported Deaths 2014-2019 vs. 2020'}#,
#                                            {'yaxes': {'range': [yMinRaw, yMaxRaw]}}
                                          ]),
                              dict(label = 'Normalized CDC Data',
                                   method = 'update',
                                   args = [{'visible': plotVisibility[1]},
                                           {'title': 'All Cause Reported Deaths about 2014-2019 Median'}#,
#                                            {'yaxes': {'range': [yMinNorm, yMaxNorm]}}
                                          ]),
                     ]),)
                     ])
    return fig
    
def mobility_plot(dfMobility, dfStateData, fips):
    stateName = dfStateData.at[str(fips).zfill(2), 'State']
    
    fig = go.Figure()

    dates = dfMobility.loc[stateName].index.values

    # Plot each column of mobility data
    for column in dfMobility:
        data = dfMobility.loc[stateName][column]
        
        # Hide raw mobility data, show means
        if 'mean' in column:
            visible = True
        else:
            visible = 'legendonly'

        fig.add_trace(go.Scatter(x = dates, y = data,
                                 name = column,
                                 visible = visible))


    fig.update_layout(
        title = {
            'text':'Relative Mobility',
            'x':0.5,
            'xanchor': 'center'},
        height = figHeight,
        width = figWidth,
        hovermode = 'x unified',
        showlegend = True,
        margin = dict(l=20, r=20, t=30, b=20),
        yaxis_tickformat = '1%',
        yaxis_zeroline = True, 
        yaxis_zerolinewidth = 2, 
        yaxis_zerolinecolor = 'black')

    return fig

def per_capita_axis(fig, dfStateData, fips):
#     def raw2capita(x):
#         return x * 10000 / int(dfStateData.at[str(fips).zfill(2), 'Population'])
#     def capita2raw(x):
#         return x * int(dfStateData.at[str(fips).zfill(2), 'Population']) / 10000
    
    pop = int(dfStateData.at[str(fips).zfill(2), 'Population'])
    capita = 10000
    
    xmax = fig.data[0].x.max()
    ymin = fig.layout.yaxis.range[0]
    ymax = fig.layout.yaxis.range[1]
        
    ymin_captia = ymin * capita / pop
    ymax_captia = ymax * capita / pop
#     print([ymin, ymin_captia, ymax, ymax_captia])

    fig.add_trace(go.Scatter(x = [xmax, xmax], 
                             y = [ymin_captia, ymax_captia],                              
                             name = 'Per Capita',
                             yaxis = 'y2',
                             visible = False))

    fig.update_layout(
        yaxis2 = dict(
            title = 'Per Capita',
            range = [ymin_captia, ymax_captia],
            titlefont_color = '#1f77b4',
            tickfont_color = '#1f77b4',
            anchor = "free",
            overlaying = "y",
            side = "left",
            position=0.15,
            showgrid=False))
                
    
#     axCapita = ax.secondary_yaxis('right', functions=(raw2capita, capita2raw), )
#     axCapita.set_ylabel('Per 10,000')
    
    return fig
        
def event_markers(fig, dfEventsState):
    
    annotates = []
    for index, eventData in dfEventsState.iterrows():
        date = datetime.strptime(eventData['Date'], '%m/%d/%y')
        fig.add_shape(type = 'line',
                      xref = 'x',
                      yref = 'paper',
                      x0 = date,
                      y0 = 0,
                      x1 = date,
                      y1 = 1,
                      line = dict(
                          color = 'Black',
                          width = 1))
        annotates = annotates + [dict(text = eventData['Event'],
                                     x = date,
                                     y = 0.1,
                                     yref = 'paper',
                                     textangle = -90,
                                     font_size = 10,
                                     opacity=1,
                                     showarrow = False,
                                     bgcolor = 'white')]


    fig.update_layout(annotations = annotates)
    
    return fig
    
#     # Add Event markers
#     ymin, ymax = ax.get_ylim()
#     ytext = ymin
#     arrowprops = {'width': 1, 'headwidth': 1, 'headlength': 1, 'shrink':0.05}
#     bbox = dict(facecolor = '1', edgecolor = 'none', alpha = 0.8, pad = 0)
#     for index, eventData in dfEventsState.iterrows():
#         ax.axvline(eventData['Date'], color = 'gray', linestyle = ':')
#         ax.annotate('  ' + eventData['Event'], xy=(eventData['Date'],ytext), xytext=(-5,0), textcoords='offset points',
#                     rotation=90, va='bottom', ha='center', annotation_clip=False, arrowprops=arrowprops, bbox=bbox)
        
def hyst(x, th_lo, th_hi, initial = False):
    """
    x : Numpy Array
        Series to apply hysteresis to.
    th_lo : float or int
        Below this threshold the value of hyst will be False (0).
    th_hi : float or int
        Above this threshold the value of hyst will be True (1).
    https://stackoverflow.com/questions/23289976/how-to-find-zero-crossings-with-hysteresis
    """        

    if th_lo > th_hi: # If thresholds are reversed, x must be reversed as well
        x = x[::-1]
        th_lo, th_hi = th_hi, th_lo
        rev = True
    else:
        rev = False

    hi = x >= th_hi
    lo_or_hi = (x <= th_lo) | hi

    ind = np.nonzero(lo_or_hi)[0]  # Index für alle darunter oder darüber
    if not ind.size:  # prevent index error if ind is empty
        x_hyst = np.zeros_like(x, dtype=bool) | initial
    else:
        cnt = np.cumsum(lo_or_hi)  # from 0 to len(x)
        x_hyst = np.where(cnt, hi[ind[cnt-1]], initial)

    if rev:
        x_hyst = x_hyst[::-1]

    return x_hyst

def inflection_points(data):
    dataSmothing = 5
    deriviativeSmoothing = 5
    hysteresisLimit = 4
    
    # Smooth raw data to get better derivatives
    dataSmoothed = data.rolling(window=dataSmothing, center=True, min_periods = 3, win_type = 'triang').mean()

    # Take second deriviative and smooth result
    secondDerivative = dataSmoothed.diff().diff()
    secondDeriSmooth = secondDerivative.rolling(window=deriviativeSmoothing, center=True, min_periods = 3, win_type = 'triang').mean()

    # Get changes in second deriviative accounting for hysteresis
    secondDerivHyst = hyst(secondDeriSmooth, -hysteresisLimit, hysteresisLimit, initial = True)
    
    # Get inflection points
    inflections = np.concatenate([[0], np.diff(secondDerivHyst.astype(float))]).astype(bool)
    
    return inflections

def figures_to_html(figs, filename):
    '''Saves a list of plotly figures in an html file.

    Parameters
    ----------
    figs : list[plotly.graph_objects.Figure]
        List of plotly figures to be saved.

    filename : str
        File name to save in.

    https://stackoverflow.com/questions/46821554/multiple-plotly-plots-on-1-page-without-subplot/59265030#59265030
    '''

    headerText = filename.split('/')[1].split('.')[0]
    space = ' '
    stateName = space.join(headerText.split(' ')[2:])
    dashboard = open(filename, 'w')
    dashboard.write("<html><head>" + 
                    "<title>" + headerText + "</title>" + "\n" + 
                    "<style>" + "\n" + 
                    "* {" + "\n" + 
                    "  box-sizing: border-box;" + "\n" + 
                    "}" + "\n" + 
                    ".plotly-graph-div {" + "\n" + 
                    "float: left;" + "\n" + 
#                     "max-width: 625px;" + "\n" + 
#                     "max-height: 50%;" + "\n" + 
#                     "min-width: 32%;" + "\n" + 
#                     "min-height: 300px;" + "\n" + 
                    "}" + "\n" + 
                    "</style></head><body>" + "\n" +
                    "<div class=\"header\">"  + "\n" +
                    "<h1>" + stateName + "</h1></div>"  + "\n" +
                    "<a href=\"https://sckilcoyne.github.io/Coivd19/\">State Index</a>" + 
                    "  <a href=\"https://github.com/sckilcoyne/Coivd19\">GitHub Project</a>")

    add_js = True
    for fig in figs:

        inner_html = pyo.plot(
            fig, include_plotlyjs=add_js, output_type='div'
        )

        dashboard.write(inner_html)
        add_js = False

    dashboard.write("</body></html>" + "\n")
    
def githubIndex(dfStateData, fipsList):
    githubURL = 'https://sckilcoyne.github.io/Coivd19/'
    fileName = 'index.md'
    
    indexFile = open(fileName, 'w')
    indexFile.write('[GitHub Project](https://github.com/sckilcoyne/Coivd19)  \n' + 
                    'Sources: [New York Times](https://github.com/nytimes/covid-19-data), ' +
                    '[Covid Tracking Project](https://covidtracking.com/), ' +
                    '[US Census](https://api.census.gov/data/2019/pep/population), \n' +
                    '[Apple](https://www.apple.com/covid19/mobility), \n' +
                    '[Google](https://www.google.com/covid19/mobility)  ')
    for fips in fipsList:
        if int(fips) in [int(i) for i in dfStateData.index.tolist()]:
            stateName = dfStateData.at[str(fips).zfill(2), 'State']
            htmlFile = 'figs/Tracking Data ' + stateName + '.html'
            indexFile.write('[' + stateName + '](' + githubURL + htmlFile + ')  \n')
            
    indexFile.close()
            