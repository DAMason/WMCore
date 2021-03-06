from __future__ import (division, print_function)

import socket
import copy
from collections import defaultdict

# From top level

WMARCHIVE_TOP_LEVEL_REMOVE_OUTSIDE_LAYER = ["steps"]
# convert data format under stpes["cmsRun1"/"logArch1"/"stageOut1"]["output"]
WMARCHIVE_REMOVE_OUTSIDE_LAYER = ["checksum", "dataset"]
# convert to list from str
WMARCHIVE_CONVERT_TO_LIST = ["OutputPFN", "lfn"]

WMARCHIVE_DATA_MAP = {"OutputPFN": "outputPFNs", "inputPath": "inputDataset",
                      "lfn": "outputLFNs", "input": "inputLFNs", "inputpfns": "inputPFNs"}


WMARCHIVE_REMOVE_FIELD = ["InputPFN", "pfn", "user_dn", "user_vogroup", "user_vorole"]
WMARCHIVE_COMBINE_FIELD = {"outputDataset": ["primaryDataset", "processedDataset", "dataTier"]}

WMARCHIVE_LFN_REF_KEY = ["lfn", "files"]
WMARCHIVE_PFN_REF_KEY = ["pfn"]
WMARCHIVE_FILE_REF_KEY = {"LFN": WMARCHIVE_LFN_REF_KEY,
                          "PFN": WMARCHIVE_PFN_REF_KEY}

ERROR_TYPE = {'exitCode': int}

PERFORMANCE_TYPE = {'cpu': {'AvgEventCPU': float,
                            'AvgEventTime': float,
                            'MaxEventCPU': float,
                            'MaxEventTime': float,
                            'MinEventCPU':  float,
                            'MinEventTime': float,
                            'TotalEventCPU': float,
                            'TotalJobCPU': float,
                            'TotalJobTime': float,
                            'EventThroughput': float,
                            'TotalLoopCPU': float,
                            'TotalInitTime': float,
                            'TotalInitCPU': float,
                            'NumberOfThreads': int,
                            'NumberOfStreams': int},
                    'memory': {'PeakValueRss': float,
                               'PeakValueVsize': float},
                    'storage': {'readAveragekB': float,
                                'readCachePercentageOps': float,
                                'readMBSec': float,
                                'readMaxMSec': float,
                                'readNumOps': float,
                                'readPercentageOps': float,
                                'readTotalMB': float,
                                'readTotalSecs': float,
                                'writeTotalMB': float,
                                'writeTotalSecs': float}}

TOP_LEVEL_STEP_DEFAULT = {'analysis': {},
                          'cleanup': {},
                          'logs': {},
                          'errors': [],
                          'input': [],
                          'output': [],
                          'performance': {}
                          }

# only composed value need to bs set default value
STEP_DEFAULT = { #'name': '',
             'analysis': {},
             'cleanup': {},
             'logs': {},
             'errors': [],
             'input': [{#'catalog': '',
                        #'events': -1,
                        #'guid': '',
                        #'input_source_class': '',
                        #'input_type': '',
                        #'lfn': -1,
                        #'module_label': '',
                        #'pfn': -1,
                        'runs': []}],
             'output': [{#'acquisitionEra': '',
                         #'adler32': '',
                         #'applicationName': '',
                         #'applicationVersion': '',
                         #'async_dest': '',
                         #'branch_hash': '',
                         #'catalog': '',
                         #'cksum': '',
                         #'configURL': '',
                         #'events': -1,
                         #'globalTag': '',
                         #'guid': '',
                         #'inputDataset': '',
                         'inputLFNs': [],
                         'inputPFNs': [],
                         #TODO change to empty string from None
                         #'location': '',
                         #'merged': False,
                         #'module_label': '',
                         #'ouput_module_class': '',
                         #'outputDataset': '',
                         'outputLFNs': [],
                         'outputPFNs': [],
                         #'prep_id': '',
                         #'processingStr': '',
                         #'processingVer': -1,
                         'runs': [],
                         #'size': -1,
                         #'validStatus': '',
                         #"SEName": '',
                         #"PNN": '',
                         #"GUID": '',
                         #'StageOutCommand': ''
                         }],
              'performance': {'cpu': {},
                              'memory': {},
                              'multicore': {},
                              'storage': {}},
              #'site': 'T2_CH_CERN',
              #'start': 1454569735,
              #'status': 0,
              #'stop': 1454569736
              }

def combineDataset(dataset):
    dataset["outputDataset"] = "/%s/%s/%s" % (dataset["primaryDataset"], dataset["processedDataset"], dataset["dataTier"])
    del dataset["primaryDataset"]
    del dataset["processedDataset"]
    del dataset["dataTier"]
    return dataset

def changeRunStruct(runDict):
    runList = []
    for run, lumis in runDict.iteritems():
        singleRun = {"runNumber": int(run)}
        if isinstance(lumis, dict):
            # In this case, lumis is a dictionary with lumi numbers as the key, event counts as the value
            singleRun.update({'lumis': [int(lumi) for lumi in lumis.keys()],
                              'eventsPerLumi': lumis.values()})
        elif isinstance(lumis, list):
            singleRun.update({'lumis': lumis})
        runList.append(singleRun)

    return runList

def _changeToFloat(value):
    if value in ["-nan", "nan", "inf", ""]:
        return -1.0
    else:
        return float(value)

def _validateTypeAndSetDefault(sourceDict, stepDefault):

    # check primitive time and remvoe if the values is composite type.
    for key, value in sourceDict.items():
        if key not in stepDefault and value in [[], {}, None, "None"]:
            del sourceDict[key]

    # set missing composite type defaut.
    for category in stepDefault:
        if (category not in sourceDict) or (category in sourceDict and not sourceDict[category]):
            sourceDict[category] = stepDefault[category]

def changePerformanceStruct(perfDict):
    return [{"pName": prop, "value": _changeToFloat(value)}  for prop, value in perfDict.items()]

def changeToList(aDict):
    return [{"prop": prop, "value": value}  for prop, value in aDict.items()]

def convertInput(inputList):
    for inputDict in inputList:
        if "runs" in inputDict:
            inputDict['runs'] = changeRunStruct(inputDict["runs"])

        _validateTypeAndSetDefault(inputDict, STEP_DEFAULT['input'][0])

    return inputList

def typeCastError(errorList):
    for errorDict in errorList:
        for key in errorDict:
            if key in ERROR_TYPE:
                value = errorDict[key]
                errorDict[key] = ERROR_TYPE[key](value)
    return errorList

def typeCastPerformance(performDict):
    newPerfDict = defaultdict(dict)
    for key in PERFORMANCE_TYPE:
        if key in performDict:
            for param in PERFORMANCE_TYPE[key]:
                if param in performDict[key]:
                    try:
                        value = performDict[key][param]
                        if value in ["-nan", "nan", "inf", ""]:
                            value = -1
                        if PERFORMANCE_TYPE[key][param] == int:
                        # the received value comes from CMSSW FWJR and its type is string
                        # Although type is int, CMSSW FWJR string is constructed as float i.e. "3.0"
                        # In that case we convert to float first before type cast to int.
                        # since int("3.0") will raise an exception but int(float("3.0") won't
                            value = float(value)
                        newPerfDict[key][param] = PERFORMANCE_TYPE[key][param](value)
                    except ValueError as ex:
                        newPerfDict[key][param] = PERFORMANCE_TYPE[key][param](-1)
                        print("key: %s, param: %s, value: %s \n%s" % (key, param,
                                                    performDict[key][param], str(ex)))
    return dict(newPerfDict)


def convertOutput(outputList):
    newOutputList = []
    for itemList in outputList:
        newOutputList.extend(itemList)

    for outDict in newOutputList:
        for field in WMARCHIVE_REMOVE_FIELD:
            if field in outDict:
                del outDict[field]

        for field in WMARCHIVE_CONVERT_TO_LIST:
            if field in outDict and isinstance(outDict[field], basestring):
                outDict[field] = [outDict[field]]

        for oldKey, newKey in WMARCHIVE_DATA_MAP.items():
            if oldKey in outDict:
                outDict[newKey] = outDict[oldKey]
                del outDict[oldKey]

        if "runs" in outDict:
            outDict['runs'] = changeRunStruct(outDict["runs"])

        if "checksums" in outDict:
            outDict.update(outDict["checksums"])
            del outDict["checksums"]

        if "dataset" in outDict:
            outDict.update(combineDataset(outDict["dataset"]))
            del outDict["dataset"]

        if "location" in outDict and isinstance(outDict["location"], list):
            if len(outDict["location"]) > 0:
                outDict["location"] = outDict["location"][0]
            else:
                outDict["location"] = ""

        _validateTypeAndSetDefault(outDict, STEP_DEFAULT['output'][0])

    return newOutputList

def convertStepValue(stepValue):
    if "status" in stepValue:
        if stepValue["status"] == "Failed":
            stepValue["status"] = 1
        else:
            stepValue["status"] = int(stepValue["status"])

    if "errors" in stepValue:
        if len(stepValue['errors']) == 0:
            stepValue['errors'] = []
        else:
            typeCastError(stepValue['errors'])

    input_keys = ['source', 'logArchives']
    if "input" in stepValue:
        if len(stepValue['input']) == 0:
            #if empty convert to list from {}
            stepValue['input'] = []

        elif len(stepValue['input']) > 1:
            # assume only one input value
            raise Exception("more than one input value %s" % stepValue['input'].keys())

        elif stepValue['input'].keys()[0] in input_keys:
            stepValue['input'] = convertInput(stepValue['input'][stepValue['input'].keys()[0]])

        else:
            raise Exception("Unknow iput key %s" % stepValue['input'].keys())

    if "output" in stepValue:
        # remove output module name layer
        stepValue['output'] = convertOutput(stepValue['output'].values())

    if "performance" in stepValue:
        stepValue["performance"] = typeCastPerformance(stepValue["performance"])
        # If it needs to chnage to list format replace to this
        #for category in stepValue["performance"]:
        #    stepValue["performance"][category] = changePerformanceStruct(stepValue["performance"][category])

        _validateTypeAndSetDefault(stepValue["performance"], STEP_DEFAULT["performance"])

    # If structure need to be changed with this uncomments
    #listConvKeys = ['analysis', 'cleanup', 'logs', 'parameters']
    #for key in listConvKeys:
    #    stepValue[key] = changeToList(stepValue[key])

    return stepValue

def convertSteps(steps):
    stepList = []
    for key, value in steps.items():
        stepItem = {}
        stepItem['name'] = key
        stepItem.update(convertStepValue(value))
        _validateTypeAndSetDefault(stepItem, TOP_LEVEL_STEP_DEFAULT)
        stepList.append(stepItem)
    return stepList

def convertToArchiverFormat(fwjr):
    """
    """
    newFWJR = copy.deepcopy(fwjr)
    if "steps" in newFWJR:
        newFWJR["steps"] = convertSteps(newFWJR["steps"])

    return newFWJR

def createFileArrayRef(fwjr, fArrayRef):

    if isinstance(fwjr, list):
        for item in fwjr:
            createFileArrayRef(item, fArrayRef)
    elif isinstance(fwjr, dict):
        for key, value in fwjr.items():
            addKeyFlag = False

            for fileType, keyList in WMARCHIVE_FILE_REF_KEY.items():
                for kw in keyList:
                    if kw in key.lower():
                        fArrayRef[fileType].add(key)
                        addKeyFlag = True

            if not addKeyFlag:
                createFileArrayRef(value, fArrayRef)
    else:
        return


def createFileArray(fwjr, fArray, fArrayRef):

    if isinstance(fwjr, dict):
        for key, value in fwjr.items():
            for fileType in WMARCHIVE_FILE_REF_KEY.keys():
                if key in fArrayRef[fileType]:
                    if isinstance(value, list):
                        for fileName in value:
                            fArray[fileType].add(fileName)
                    else: # this should be string
                        fArray[fileType].add(value)
            createFileArray(value, fArray, fArrayRef)
    elif isinstance(fwjr, list):
        for item in fwjr:
            createFileArray(item, fArray, fArrayRef)
    else:
        return

def changeToFileRef(fwjr, fArray, fArrayRef):

    if isinstance(fwjr, dict):
        for key, value in fwjr.items():
            for fileType in WMARCHIVE_FILE_REF_KEY.keys():
                if key in fArrayRef[fileType]:
                    if isinstance(value, list):
                        newRef = []
                        for fileName in value:
                            index = fArray[fileType].index(fileName)
                            newRef.append(index)
                    else: # this should be string
                        newRef = fArray[fileType].index(value)
                    fwjr[key] = newRef
            changeToFileRef(value, fArray, fArrayRef)
    elif isinstance(fwjr, list):
        for item in fwjr:
            changeToFileRef(item, fArray, fArrayRef)
    else:
        return

def createArchiverDoc(job, version=None):
    """
    job_id is jobid + retry count same as couch db _id
    """

    job_id = job["id"]
    fwjr = job['doc']["fwjr"]
    jobtype = job['doc']["jobtype"]
    jobstate = job['doc']['jobstate']
    create_ts = job['doc']['timestamp']
    newfwjr = convertToArchiverFormat(fwjr)

    fArrayRef = {}
    fArray = {}
    for fileType in WMARCHIVE_FILE_REF_KEY.keys():
        fArrayRef[fileType] = set()
        fArray[fileType] = set()

    createFileArrayRef(newfwjr, fArrayRef)

    for fileType in WMARCHIVE_FILE_REF_KEY.keys():
        fArrayRef[fileType] = list(fArrayRef[fileType])

    createFileArray(newfwjr, fArray, fArrayRef)

    for fileType in WMARCHIVE_FILE_REF_KEY.keys():
        fArray[fileType] = list(fArray[fileType])


    changeToFileRef(newfwjr, fArray, fArrayRef)

    #convert to fwjr format

    for fileType in WMARCHIVE_FILE_REF_KEY.keys():
        newfwjr["%sArrayRef" % fileType] = fArrayRef[fileType]
        newfwjr["%sArray" % fileType] = fArray[fileType]

    if version == None:
        # add this trry to remove the dependency on WMCore code.
        import WMCore
        version = WMCore.__version__
    # append meta data in fwjr
    wnName = ""
    if "WorkerNodeInfo" in fwjr:
        wnName = fwjr["WorkerNodeInfo"].get("HostName", "")

    newfwjr['meta_data'] = {'agent_ver': version,
                         'host': socket.gethostname().lower(),
                         'wn_name': wnName,
                         'fwjr_id': job_id,
                         'jobtype': jobtype,
                         'jobstate': jobstate,
                         'ts': create_ts
                         }
    return newfwjr
