
from PyQt5 import QtCore
import threading
import dataTools.UnitConverter as uc

from graphTools.Grapher import *
from interface.SignalConnector import *
import Config



class LiveGrapher(Grapher):
    """ A class for plotting collected data into the graph are of the UI.
        This class allows for graphing data as its collected, graphing old data,
        and clearing the graph. """

    def __init__(self, graphHandle):
        """ Creates a new grapher object for visualizing collected data.
        Parameters:
            graphHandle: The pyqtplot widget used in the UI """
        super().__init__(graphHandle)

        # set up line colors
        self.redPen = pg.mkPen('r', width=Config.GRAPH_LINE_WIDTH)
        self.bluePen = pg.mkPen('b', width=Config.GRAPH_LINE_WIDTH)

        self.dataIndex = 0
        self.data = MeasurementData([0]*50000,[0]*50000,[0]*50000,[0]*50000)
        # add the two data series for load and displacement data
        self.loadLines.append(self.graph.plot(self.data.sample, self.data.load, pen=self.redPen))
        self.stepLines.append(self.graph.plot(self.data.sample, self.data.step, pen=self.bluePen))
        self.loadStepLines.append(self.graph.plot(self.data.step, self.data.load, pen=self.redPen))
        self.lock = threading.Lock() # lock for controlling access to graph data

        # default to time series when setting up the graph axes
        self.setupTimeSeries()
        return


    def setupTimeSeries(self):
        super().setupTimeSeries()
        self.refreshPlot()
        return


    def setupLoadDisplacementGraph(self):
        super().setupLoadDisplacementGraph()
        self.refreshPlot()
        return


    def startLiveUpdate(self):
        # set up a process for refreshing the graph with newly collected data
        self.timer = QtCore.QTimer()
        self.timer.setInterval(Config.GRAPH_REFRESH_DELAY)
        self.timer.timeout.connect(self.refreshPlot)
        self.timer.start()
        print("timer started")


    def stopLiveUpdate(self):
        self.timer.stop()
        self.refreshPlot()


    def refreshPlot(self):
        """ Refreshes the graph display with any newly collected data. """

        self.lock.acquire()
        # if we are showing a time series
        if(self.view == 0):
            self.loadLines[0].setData((self.data.sample[0:self.dataIndex])[::Config.GRAPH_POINT_SKIP], (self.data.load[0:self.dataIndex])[::Config.GRAPH_POINT_SKIP])
            self.stepLines[0].setData((self.data.sample[0:self.dataIndex])[::Config.GRAPH_POINT_SKIP], (self.data.step[0:self.dataIndex])[::Config.GRAPH_POINT_SKIP])
        # if we are showing the force as a function of displacement
        elif(self.view == 1):
            self.loadStepLines[0].setData(self.data.step[0:self.dataIndex:Config.GRAPH_POINT_SKIP], self.data.load[0:self.dataIndex:Config.GRAPH_POINT_SKIP])
        self.lock.release()
        return


    def markInitialApproachStart(self):
        self.lock.acquire()
        if self.data.step == []:
            self.data.initialApproachStart = 1
        else:
            self.data.initialApproachStart = self.data.sample[-1]
        self.lock.release()
        return


    def markPreloadHoldStart(self):
        self.lock.acquire()        
        self.data.preloadHoldStart = self.data.sample[-1]
        self.lock.release()
        return


    def markMainApproachStart(self):
        self.lock.acquire()
        self.data.mainApproachStart = self.data.sample[-1]
        self.lock.release()
        return


    def markMainHoldStart(self):
        self.lock.acquire()
        self.data.mainHoldStart = self.data.sample[-1]
        self.lock.release()
        return


    def markRetractStart(self):
        self.lock.acquire()
        self.data.retractStart = self.data.sample[-1]
        self.lock.release()
        return


    def addDataPoint(self, dataPoint):
        """ Adds a single data point to the end of the graph.
        Parameters:
            step (int): the displacemet for this data point
            load (float): the load value for this data point """

        self.lock.acquire()
        # if this is the first data point in the series
        if self.data.sample == []:
            self.data.sample.append(1)
        # else increment the sample number by 1 and append
        else:
            self.data.sample[self.dataIndex] = self.dataIndex +1

        self.data.step[self.dataIndex] = dataPoint[0]
        self.data.load[self.dataIndex] = dataPoint[1]
        self.data.phase[self.dataIndex] = dataPoint[2]

        self.dataIndex += 1
        self.lock.release()
        return


    def addDataFromPipe(self, dataQueue):
        """ Starts a process to add data points to the end of the graph from a pipe.
        Parameters:
            pipe (Pipe): the pipe to read data from """

        # start performing live updates to the graph screen
        self.startLiveUpdate()

        # set up a signal handler to stop live updates when the pipe closes
        self.signalManager = SignalConnector()
        self.signalManager.connect(self.stopLiveUpdate)
        self.signalManager.start()

        # start the thread to accept data over the pipe
        self.pipeManagerhandle= threading.Thread(name = 'pipeManager', target = pipeManager, args=(self, dataQueue, self.signalManager))
        self.pipeManagerhandle.start()
        return


    def setData(self, graphData):
        """ Sets all of the data for the series in the graph.
        Parameters:
            x (int): array of sample numbers to be graphed
            step (float): array of displacement data to be graphed
            load (float): array of load data to be graphed """

        self.lock.acquire()
        self.data = graphData
        self.loadLines[0].setData(self.data.sample, self.data.load)
        self.stepLines[0].setData(self.data.sample, self.data.step)
        self.loadStepLines[0].setData(self.data.step, self.data.load)
        self.lock.release()
        
        # default back to a time series
        self.setupTimeSeries()
        return


    def getData(self):
        """ Gets all of the data currently shown in the graph.
        Returns:
            xData (int): array of sample numbers
            stepData (int): array of displacement data
            loadData (fload): array of load data """

        return self.data


    def clear(self):
        """ Clears the collected data and the graph area. """

        self.lock.acquire()
        super().clear()
        self.dataIndex = 0
        self.data = MeasurementData([0]*50000,[0]*50000,[0]*50000,[0]*50000)
        self.loadLines.append(self.graph.plot(self.data.sample, self.data.load, pen=self.redPen))
        self.stepLines.append(self.graph.plot(self.data.sample, self.data.step, pen=self.bluePen))
        self.loadStepLines.append(self.graph.plot(self.data.step, self.data.load, pen=self.redPen))
        self.lock.release()
        self.refreshPlot()
        return



def pipeManager(self, dataQueue, pipeEndSignal):
    """ The thread function responsible for loading data from the pipe and 
    plotting it to the graph area. """
    count = 0
    rawData = None
    done = False # pipe EOF
    while not done:          
        # graph the data waiting in the pipe
        try:
            count +=1

            data = dataQueue.get()
            if data == None: 
                return
            
            rawData = list(data)

            rawData[0] = rawData[0] / 100 # scale the displacement
            rawData[1] = uc.rawADCToNewton(rawData[1]) # convert load from adc reading to newtons
            self.addDataPoint(rawData)

        except EOFError:
            done = True
    print("closing the pipe")
    print(count)
    print(rawData)
    pipeEndSignal.setAsyncSignal()
    return