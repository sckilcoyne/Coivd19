import pandas as pd
import numpy as np
import matplotlib.pyplot as plt 
import matplotlib.ticker as mtick
from matplotlib.ticker import FormatStrFormatter
import plotly

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
    fig = plt.figure(figsize=(plotCols * 10, plotRows * 5))
    axTrackingRaw = fig.add_subplot(plotRows, plotCols, 1)
    axTrackingLog = fig.add_subplot(plotRows, plotCols, 2)
    axReffectEsti = fig.add_subplot(plotRows, plotCols, 3)
    axCorrelation = fig.add_subplot(plotRows, plotCols, 4)
    axTestingDays = fig.add_subplot(plotRows, plotCols, 5)
    axTestingGrow = fig.add_subplot(plotRows, plotCols, 6)
    axTestPercent = fig.add_subplot(plotRows, plotCols, 7)
    axResourceRaw = fig.add_subplot(plotRows, plotCols, 8)
    axResourceLog = fig.add_subplot(plotRows, plotCols, 9)   
    
    # Tracking Plots
    tracking_plot(axTrackingRaw, dfCovid, fips)
    tracking_plot(axTrackingLog, dfCovid, fips)
    axTrackingLog.set(yscale = 'log')
    
    # R effective estimate plot
    r_effective_plot(axReffectEsti, dfCovid, fips)
    
    # Correlation Plot
    correlation_plot(axCorrelation, dfShiftCor, fips)
    
    # Daily Testing Plot
    daily_testing_plot(axTestingDays, dfCovid, fips)
    
    # Testing Growth Plot
    testing_growth_plot(axTestingGrow, dfCovid, fips)
    
    # Percent Positive Plot
    percent_poisitve_plot(axTestPercent, dfCovid, fips)
    
    # Resource Usage Plots
    resource_usage_plot(axResourceRaw, dfCovid, fips)
    resource_usage_plot(axResourceLog, dfCovid, fips)
    axResourceLog.set(yscale = 'log')
    
    # Add per capita axis
    perCapAx = [axTrackingRaw, axTrackingLog, axTestingDays, 
                axTestingGrow, axResourceRaw, axResourceLog]
    for ax in perCapAx:
        per_capita_axis(ax, dfStateData, fips)    
        
    # Add event markers
    for ax in [axTrackingRaw, axTrackingLog, axReffectEsti]:
        event_markers(ax, dfEventsState)
        
    # Set X limits
    xlimAx = [axTrackingRaw, axTrackingLog, axReffectEsti, axTestingDays, 
              axTestPercent, axTestingGrow, axResourceRaw, axResourceLog]
    for ax in xlimAx:
        ax.set(xlim = plotDateRange)
        
    # Overall figure formatting   
    fig.suptitle(dfStateData.at[str(fips).zfill(2), 'State'],
                fontsize = 18,
                fontweight = 'bold')
    fig.tight_layout(rect=[0, 0.03, 1, 0.97])
    plt.savefig('figs/Tracking Data ' + dfStateData.at[str(fips).zfill(2), 'State'])
#     plt.close(fig)

# https://stackoverflow.com/questions/52615425/matplotlib-to-plotly-offline
#     plotly_fig = plotly.tools.mpl_to_plotly(fig)
#     plotlyFile = 'figs/Tracking Data ' + dfStateData.at[str(fips).zfill(2), 'State'] + '.html'
#     plotly.offline.plot(plotly_fig, filename = plotlyFile)
    
    
def tracking_plot(ax, dfCovid, fips):
    ax.plot(dfCovid.loc[fips]['positive_cases'], label = 'Reported Cases  (NYT: CTP--)', color = 'tab:blue')
    ax.plot(dfCovid.loc[fips]['cases(NYT)'], color = 'tab:blue', linestyle = ':') # , label = 'Reported Cases (NYT)'
    ax.plot(dfCovid.loc[fips]['positive(CTP)'], color = 'tab:blue', linestyle = '--') # , label = 'Reported Cases (CTP)'
    cases = dfCovid.loc[fips]['positive_cases'].copy()
    inflections = inflection_points(cases)
    ax.scatter(cases.index[inflections],cases[inflections], label = 'Case Inflection Points', marker='o', color='tab:red')

    
    ax.plot(dfCovid.loc[fips]['deaths'], label = 'Deaths (NYT: CTP--)', color = 'tab:orange')
    ax.plot(dfCovid.loc[fips]['deaths(NYT)'], color = 'tab:orange', linestyle = ':') # , label = 'Deaths (NYT)'
    ax.plot(dfCovid.loc[fips]['death(CTP)'], color = 'tab:orange', linestyle = '--') # , label = 'Deaths (CTP)'
    
    if dfCovid.loc[fips]['hospitalizedCumulative(CTP)'].sum() > 0:
        ax.plot(dfCovid.loc[fips]['hospitalizedCumulative(CTP)'], label = 'Hospitalized Cum. (CTP)', color = 'tab:green')
    if dfCovid.loc[fips]['inIcuCumulative(CTP)'].sum() > 0:
        ax.plot(dfCovid.loc[fips]['inIcuCumulative(CTP)'], label = 'ICU Cum. (CTP)', color = 'tab:red')
    if dfCovid.loc[fips]['onVentilatorCumulative(CTP)'].sum() > 0:
        ax.plot(dfCovid.loc[fips]['onVentilatorCumulative(CTP)'], label = 'Ventilator Cum. (CTP)', color = 'tab:purple')
    if dfCovid.loc[fips]['recovered(CTP)'].sum() > 0:
        ax.plot(dfCovid.loc[fips]['recovered(CTP)'], label = 'Recovered (CTP)', color = 'tab:brown')    
        
    recovered = dfCovid.loc[fips]['recovered(CTP)'].copy()
    recovered[np.isnan(recovered)] = 0
    knownNonActive = np.add(dfCovid.loc[fips]['deaths'], recovered)
    upperLimitActive = dfCovid.loc[fips]['positive_cases'] - knownNonActive
    ax.plot(upperLimitActive, label = 'Positive less Recovered and Dead', color = 'tab:pink', linestyle = ':', linewidth = 3)
    
    estActive = pd.DataFrame(dfCovid.loc[fips]['positive_cases']).reset_index()
    estActive['date'] = estActive['date'] + pd.Timedelta(days = 14)
    estActive = estActive.set_index(['date'])
    estActive['est_active'] = dfCovid.loc[fips]['positive_cases'] - estActive['positive_cases']
    ax.plot(estActive.index, estActive['est_active'], label = 'Estimated Active (14 day case life)', 
             color = 'tab:gray', linestyle = ':', linewidth = 3)
    
    ax.set(title = 'Cumulative Tracking Data')
    ax.legend()
    
def r_effective_plot(ax, dfCovid, fips):
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
        
        ax.plot(Reff, label = str(T) + ' day Observed R = ' + str(Reff[-1].round(2)), linestyle = ':')
        ax.plot(ReffScale, label = str(T) + ' day Adjusted R ' + str(ReffScale[-1].round(2)) , linestyle = '--')
       
    ax.set(
        title = 'R estimates from Positive results',
#         xlim = [firstDate, currentDate],
        ylim = [0.6, 6],
        yscale = 'log')
    ax.legend()
    ax.grid(axis = 'y', which = 'both')
    ax.yaxis.tick_right()
    ax.yaxis.set_minor_formatter(FormatStrFormatter('%.1f'))
    ax.yaxis.set_major_formatter(FormatStrFormatter('%.1f'))
    
def correlation_plot(ax, dfShiftCor, fips):
    caseDeathCor = dfShiftCor.loc[fips,dfShiftCor.columns.str.match('Shift_\d')]
    caseDeathCorLog = dfShiftCor.loc[fips,dfShiftCor.columns.str.match('Shift_log_')]
    caseAutoCor = dfShiftCor.loc[fips,dfShiftCor.columns.str.match('Case_autocorr_\d')]
    caseAutoCorLog = dfShiftCor.loc[fips,dfShiftCor.columns.str.match('Case_autocorr_log_')]
    
    shiftRange = int(dfShiftCor.columns[-1].split('_')[-1]) + 1
    ax.plot(range(shiftRange),caseDeathCor, label = 'Case vs. Deaths Shifted, Raw')
    ax.plot(range(shiftRange),caseDeathCorLog, label = 'Case vs. Deaths Shifted, Log-Log')
    ax.plot(range(shiftRange),caseAutoCor, label = 'Case Autocorrelation, Raw')
    ax.plot(range(shiftRange),caseAutoCorLog, label = 'Case Autocorrelation, Log')
    
    ax.set(
        title = 'Cases related to X days later',
        xticks = range(0,shiftRange,2), 
        xticklabels = range(0,shiftRange,2),
        xlabel = 'Days later', 
        xlim = [0, shiftRange - 1],
        ylim = [0.7, 1])
    ax.legend()
    
def daily_testing_plot(ax, dfCovid, fips):
    dailyTesting = dfCovid.loc[fips]['positive_cases'].diff() + dfCovid.loc[fips]['negative(CTP)'].diff()
    dates = dfCovid.loc[fips].index
    
    ax.scatter(dates, dailyTesting, label = 'Daily Testing', marker = '.', color = 'tab:gray')
    dailyMoving3 = dailyTesting.rolling(window=3).mean()
    dailyMoving7 = dailyTesting.rolling(window=7).mean()
    ax.plot(dates, dailyMoving3, label = 'Daily Testing (3 day)')
    ax.plot(dates, dailyMoving7, label = 'Daily Testing (7 day)')
    
    ax_ymin = min(dailyMoving3.min(), dailyMoving7.min(), 0) * 1.1
    ax_ymax = max(dailyMoving3.max(), dailyMoving7.max()) * 1.1
    ax.set(
        title = 'Daily Testing',
        ylim = [ax_ymin, ax_ymax])
    ax.legend()
    
def testing_growth_plot(ax, dfCovid, fips):
    ax.axhline(y=0, color='dimgray', linewidth = 1)
    
    dailyTesting = dfCovid.loc[fips]['positive_cases'].diff() + dfCovid.loc[fips]['negative(CTP)'].diff()
    testingGrowth = dailyTesting.diff()
    dates = dfCovid.loc[fips].index
    
    ax.scatter(dates, testingGrowth, label = 'Daily Testing Growth', marker = '.', color = 'tab:gray')
    growthMoving3 = testingGrowth.rolling(window=3).mean()
    growthMoving7 = testingGrowth.rolling(window=7).mean()
    ax.plot(dates, growthMoving3, label = 'Testing Growth (3 day)')
    ax.plot(dates, growthMoving7, label = 'Testing Growth (7 day)')
    
    ax_ymin = min(growthMoving3.min(), growthMoving7.min(), 0) * 1.1
    ax_ymax = max(growthMoving3.max(), growthMoving7.max()) * 1.1
    ax.set(
        title = 'Testing Growth',
        ylim = [ax_ymin, ax_ymax])
    ax.legend()
    
def percent_poisitve_plot(ax, dfCovid, fips):
    dates = dfCovid.loc[fips].index
    totalTests = dfCovid.loc[fips]['positive_cases'] + dfCovid.loc[fips]['negative(CTP)']
    percentPositive = dfCovid.loc[fips]['positive_cases'] / totalTests
    percentPositive3day = percentPositive.rolling(window=3).mean()
    percentPositive7day = percentPositive.rolling(window=7).mean()

    positiveIncrease = dfCovid.loc[fips]['positive_cases'].diff()
    percentPosNew = positiveIncrease / totalTests.diff()
    percentPosNew3day = percentPosNew.rolling(window=3).mean()
    percentPosNew7day = percentPosNew.rolling(window=7).mean()

    ax.scatter(dates,percentPositive, label = '% Positive Results Total', color = 'tab:blue', marker = '.')
    ax.plot(dates,percentPositive3day, label = '% Positive Results Total (3 day)', color = 'tab:blue', linestyle = '--')
    ax.plot(dates,percentPositive7day, label = '% Positive Results Total (7 day)', color = 'tab:blue', linestyle = ':')

    ax.scatter(dates,percentPosNew, label = '% New Positive Results Total', color = 'tab:orange', marker = '.')
    ax.plot(dates,percentPosNew3day, label = '% New Positive Results Total (3 day)', color = 'tab:orange', linestyle = '--')
    ax.plot(dates,percentPosNew7day, label = '% New Positive Results Total (7 day)', color = 'tab:orange', linestyle = ':')
    
    ax.set(
        title = 'Positive Test Results')
    ax.yaxis.set_major_formatter(mtick.PercentFormatter(xmax=1))
    ax.legend()
    
def resource_usage_plot(ax, dfCovid, fips):
    plots = False
    if dfCovid.loc[fips]['hospitalizedCurrently(CTP)'].sum() > 0:    
        ax.plot(dfCovid.loc[fips]['hospitalizedCurrently(CTP)'], label = 'Hospitalized (CTP)', color = 'tab:blue')
        plots = True
    if dfCovid.loc[fips]['inIcuCurrently(CTP)'].sum() > 0:    
        ax.plot(dfCovid.loc[fips]['inIcuCurrently(CTP)'], label = 'ICU (CTP)', color = 'tab:orange')
        plots = True
    if dfCovid.loc[fips]['onVentilatorCurrently(CTP)'].sum() > 0:    
        ax.plot(dfCovid.loc[fips]['onVentilatorCurrently(CTP)'], label = 'On Ventilator (CTP)', color = 'tab:green')
        plots = True

    if plots:
        ax.set(
            title = 'Current Resource Usuage')
        ax.legend()
    
def per_capita_axis(ax, dfStateData, fips):
    def raw2capita(x):
        return x * 10000 / int(dfStateData.at[str(fips).zfill(2), 'Population'])
    def capita2raw(x):
        return x * int(dfStateData.at[str(fips).zfill(2), 'Population']) / 10000
    
    axCapita = ax.secondary_yaxis('right', functions=(raw2capita, capita2raw), )
    axCapita.set_ylabel('Per 10,000')
        
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