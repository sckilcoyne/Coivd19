import pandas as pd
import numpy as np
# import matplotlib.pyplot as plt 
 
import matplotlib.ticker as mtick
from matplotlib.ticker import FormatStrFormatter
import plotly
import plotly.express as px
import plotly.graph_objects as go
import plotly.figure_factory as ff
import plotly.offline as pyo

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

def state_plot(dfCovid, dfShiftCor, dfStateData, dfEvents, fips, plotDateRange):
    # Notable Events
    dfEventsAll = dfEvents.groupby('FIPS').get_group('All')
    if str(fips).zfill(2) in dfEvents.groupby('FIPS').groups.keys():
        dfEventsState = dfEventsAll.append(dfEvents.groupby('FIPS').get_group(str(fips).zfill(2)))
    else:
        dfEventsState = dfEventsAll

    # Create Figure with subplots
    plotCols = 3
    plotRows = 3      
    
    # Tracking Plots
    figTrackingRaw = tracking_plot(dfCovid, fips)
    figTrackingLog = tracking_plot(dfCovid, fips)
    figTrackingLog.update_layout(yaxis_type="log")
    
    # R effective estimate plot
    figReffective = r_effective_plot(dfCovid, fips)
    
    # Correlation Plot
    figCorrelation = correlation_plot(dfShiftCor, fips)
    
    # Daily Testing Plot
    figDailyTesting = daily_testing_plot(dfCovid, fips)
    
    # Testing Growth Plot
    figTestingGrow = testing_growth_plot(dfCovid, fips)
    
    # Percent Positive Plot
    figTestPercent = percent_poisitve_plot(dfCovid, fips)
    
    # Resource Usage Plots
    figResourceRaw = resource_usage_plot(dfCovid, fips)
    figResourceLog = resource_usage_plot(dfCovid, fips)
    figResourceLog.update_layout(yaxis_type="log")
    
    # Add per capita axis
    perCapFig = [figDailyTesting, figTestingGrow]
#     perCapFig = [figTrackingRaw, figTrackingLog, figDailyTesting, 
#                 figTestingGrow, figResourceRaw, figResourceLog]
    for fig in perCapFig:
        fig = per_capita_axis(fig, dfStateData, fips)
        
    # Add event markers
#     for ax in [axTrackingRaw, axTrackingLog, axReffectEsti]:
#         event_markers(ax, dfEventsState)
        
    # Set X limits
    xlimFig = [figTrackingRaw, figTrackingLog, figReffective, figDailyTesting, 
              figTestPercent, figTestingGrow, figResourceRaw, figResourceLog]
    for fig in xlimFig:
        fig.update_layout(xaxis_range = plotDateRange)
#         ax.set(xlim = plotDateRange)
        
    # Overall figure formatting     
    figList = [figTrackingRaw, figTrackingLog, figReffective, 
               figCorrelation, figDailyTesting,figTestingGrow,
               figTestPercent, figResourceRaw, figResourceLog]
    htmlFile = 'figs/Tracking Data ' + dfStateData.at[str(fips).zfill(2), 'State'] + '.html'
    figures_to_html(figList, htmlFile)

    
    
# def tracking_plot(fig, dfCovid, fips):
def tracking_plot(dfCovid, fips):
    fig = go.Figure()
    fig.add_trace(go.Scatter(x = dfCovid.loc[fips]['positive_cases'].index, y = dfCovid.loc[fips]['positive_cases'],
                             mode='lines',
                             name='Reported Cases (NYT, CTP)'))
    fig.add_trace(go.Scatter(x = dfCovid.loc[fips]['cases(NYT)'].index, y = dfCovid.loc[fips]['cases(NYT)'],
                             mode='markers',
                             name='Reported Cases  (NYT)',
                             visible='legendonly'))
    fig.add_trace(go.Scatter(x = dfCovid.loc[fips]['positive(CTP)'].index, y = dfCovid.loc[fips]['positive(CTP)'],
                             mode='markers',
                             name='Reported Cases  (CTP)',
                             visible='legendonly'))
     
    cases = dfCovid.loc[fips]['positive_cases'].copy()
    inflections = inflection_points(cases)
    fig.add_trace(go.Scatter(x = cases.index[inflections], y = cases[inflections],
                             mode='markers',
                             name='Case Inflection Points'))
    
    fig.add_trace(go.Scatter(x = dfCovid.loc[fips]['deaths'].index, y = dfCovid.loc[fips]['deaths'],
                             mode='lines',
                             name='Deaths (NYT, CTP)'))
    fig.add_trace(go.Scatter(x = dfCovid.loc[fips]['deaths(NYT)'].index, y = dfCovid.loc[fips]['deaths(NYT)'],
                             mode='markers',
                             name='Deaths (NYT)',
                             visible='legendonly'))
    fig.add_trace(go.Scatter(x = dfCovid.loc[fips]['death(CTP)'].index, y = dfCovid.loc[fips]['death(CTP)'],
                             mode='markers',
                             name='Deaths (CTP)',
                             visible='legendonly'))
    
    if dfCovid.loc[fips]['hospitalizedCumulative(CTP)'].sum() > 0:
        hospitalized = dfCovid.loc[fips]['hospitalizedCumulative(CTP)']
        fig.add_trace(go.Scatter(x = hospitalized.index, y = hospitalized,
                                 mode='lines',
                                 name='Hospitalized Cum. (CTP)'))        
    if dfCovid.loc[fips]['inIcuCumulative(CTP)'].sum() > 0:
        fig.add_trace(go.Scatter(x = dfCovid.loc[fips]['inIcuCumulative(CTP)'].index, y = dfCovid.loc[fips]['inIcuCumulative(CTP)'],
                                 mode='lines',
                                 name='ICU Cum. (CTP)')) 
    if dfCovid.loc[fips]['onVentilatorCumulative(CTP)'].sum() > 0:
        onVent = dfCovid.loc[fips]['onVentilatorCumulative(CTP)']
        fig.add_trace(go.Scatter(x = onVent.index, y = onVent,
                                 mode='lines',
                                 name='Ventilator Cum. (CTP)')) 
    if dfCovid.loc[fips]['recovered(CTP)'].sum() > 0:
        fig.add_trace(go.Scatter(x = dfCovid.loc[fips]['recovered(CTP)'].index, y = dfCovid.loc[fips]['recovered(CTP)'],
                                 mode='lines',
                                 name='Recovered (CTP)')) 
    # Reported de-active        
    recovered = dfCovid.loc[fips]['recovered(CTP)'].copy()
    recovered[np.isnan(recovered)] = 0
    knownNonActive = np.add(dfCovid.loc[fips]['deaths'], recovered)
    upperLimitActive = dfCovid.loc[fips]['positive_cases'] - knownNonActive
    fig.add_trace(go.Scatter(x = upperLimitActive.index, y = upperLimitActive,
                             mode='lines',
                             name='Positive less Recovered and Dead'))

    # Estimated Active
    estActive = pd.DataFrame(dfCovid.loc[fips]['positive_cases']).reset_index()
    estActive['date'] = estActive['date'] + pd.Timedelta(days = 14)
    estActive = estActive.set_index(['date'])
    estActive['est_active'] = dfCovid.loc[fips]['positive_cases'] - estActive['positive_cases']
    fig.add_trace(go.Scatter(x = estActive.index, y = estActive['est_active'],
                             mode='lines',
                             name='Estimated Active (14 day case life)'))    

    # Fig formatting
    fig.update_layout(
        title = 'Cumulative Tracking Data',
        template = "plotly_dark",
        showlegend = True,
        legend_orientation = "h",
        legend_font_size = 10,
        margin=dict(l=20, r=20, t=30, b=20))
    return fig
    
def r_effective_plot(dfCovid, fips):
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
        title = 'Estimated R',
        yaxis_type = "log",
        yaxis_range = [-.2, .8],
        template = "plotly_dark",
        showlegend = True,
        legend_orientation = "h",
        margin=dict(l=20, r=20, t=30, b=20))
# #         xlim = [firstDate, currentDate],
    
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
                             visible='legendonly'))
    fig.add_trace(go.Scatter(x = x_data, y = caseAutoCorLog,
                             mode = 'lines',
                             name = 'Case Autocorrelation, Log',
                             visible='legendonly'))
        
    # Fig formatting
    fig.update_layout(
        title = 'Cases related to X days later',
        yaxis_range = [0.7, 1],
#         xaxis_title = 'Days Later',
        template = "plotly_dark",
        showlegend = True,
        legend_orientation = "h",
        margin=dict(l=20, r=20, t=30, b=20))
#     fig.show()
    return fig
    
def daily_testing_plot(dfCovid, fips):
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
        title = 'Daily Testing',
        yaxis_range = [fig_ymin, fig_ymax],
        template = "plotly_dark",
        showlegend = True,
        legend_orientation = "h",
        margin=dict(l=20, r=20, t=30, b=20))
#     fig.show()
    return fig
    
    
def testing_growth_plot(dfCovid, fips):
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
        title = 'Testing Growth',
        yaxis_range = [fig_ymin, fig_ymax],
        template = "plotly_dark",
        showlegend = True,
        legend_orientation = "h",
        margin=dict(l=20, r=20, t=30, b=20))
                
#     fig.show()
    return fig
    
def percent_poisitve_plot(dfCovid, fips):
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
        title = 'Positive Test Results',
        yaxis_tickformat = '1%',
        yaxis_range = [0, 0.6],
        template = "plotly_dark",
        showlegend = True,
        legend_orientation = "h",
        margin=dict(l=20, r=20, t=30, b=20))
#     fig.show()
    return fig
    
def resource_usage_plot(dfCovid, fips):
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
            title = 'Current Resource Usuage')
    else:
        fig.update_layout(
            title = 'No data on Resource Usuage')
        
    # Fig formatting
    fig.update_layout(
        template = "plotly_dark",
        showlegend = True,
        legend_orientation = "h",
        margin=dict(l=20, r=20, t=30, b=20))
#     fig.show()
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
        
def event_markers(ax, dfEventsState):
    # Add Event markers
    ymin, ymax = ax.get_ylim()
    ytext = ymin
    arrowprops = {'width': 1, 'headwidth': 1, 'headlength': 1, 'shrink':0.05}
    bbox = dict(facecolor = '1', edgecolor = 'none', alpha = 0.8, pad = 0)
    for index, eventData in dfEventsState.iterrows():
        ax.axvline(eventData['Date'], color = 'gray', linestyle = ':')
        ax.annotate('  ' + eventData['Event'], xy=(eventData['Date'],ytext), xytext=(-5,0), textcoords='offset points',
                    rotation=90, va='bottom', ha='center', annotation_clip=False, arrowprops=arrowprops, bbox=bbox)
        
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
    stateName = headerText.split(' ')[2]
    dashboard = open(filename, 'w')
    dashboard.write("<html><head>" + 
                    "<title>" + headerText + "</title>" + "\n" + 
                    "<style>" + "\n" + 
                    "* {" + "\n" + 
                    "  box-sizing: border-box;" + "\n" + 
                    "}" + "\n" + 
                    ".plotly-graph-div {" + "\n" + 
                    "float: left;" + "\n" + 
                    "max-width: 625px;" + "\n" + 
                    "max-height: 50%;" + "\n" + 
                    "min-width: 32%;" + "\n" + 
                    "min-height: 300px;" + "\n" + 
                    "}" + "\n" + 
                    "</style></head><body>" + "\n" +
                    "<div class=\"header\">"  + "\n" +
                    "<h1>" + stateName + "</h1></div>"  + "\n" +
                    "<a href=\"https://sckilcoyne.github.io/Coivd19/\">State Index</a>")

    add_js = True
    for fig in figs:

        inner_html = pyo.plot(
            fig, include_plotlyjs=add_js, output_type='div'
        )

        dashboard.write(inner_html)
        add_js = False

    dashboard.write("</body></html>" + "\n")
    
def githubIndex(dfStateData, fipsList):
    githubURL = 'https://sckilcoyne.github.io/Coivd19/figs/'
    fileName = 'index.md'
    
    indexFile = open(fileName, 'w')
    for fips in fipsList:
        if int(fips) in [int(i) for i in dfStateData.index.tolist()]:
            stateName = dfStateData.at[str(fips).zfill(2), 'State']
            htmlFile = 'figs/Tracking Data ' + stateName + '.html'
            indexFile.write('[' + stateName + '](' + githubURL + htmlFile + ')  \n')
            
    indexFile.close()
            