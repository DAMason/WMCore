#!/usr/bin/env python
"""
Use WMSpecParser to extract information for creating workflow, fileset, and subscription
"""
__revision__ = "$Id: WMBSHelper.py,v 1.7 2009/08/24 14:59:40 sryu Exp $"
__version__ = "$Revision: 1.7 $"
from sets import Set

from WMCore.WMBS.File import File
from WMCore.WMBS.Workflow import Workflow
from WMCore.WMBS.Fileset import Fileset
from WMCore.WMBS.Subscription import Subscription

class WMBSHelper:

    def __init__(self, wmSpec, blockName):
        #TODO: 
        # 1. get the top level task.
        # 2. get the top level step and input
        # 3. generated the spec, owner, name from task
        # 4. get input file list from top level step
        # 5. generate the file set from work flow.
        self.wmSpec = wmSpec
        self.block = blockName or None
        self.fileset = None
        self.workflow = None
        self.subscription = None

    def createWorkflow(self):
        # create workflow
        # make up workflow name from task name
        workflowName = self.wmSpec.name
        if self.workflow == None:
            self.workflow = Workflow(self.wmSpec.specUrl,
                                 self.wmSpec.owner, workflowName,
                                 self.wmSpec.topLevelTaskName)
            self.workflow.create()

        return self.workflow

    def createFilesset(self):
        # create fileset
        # make up fileset name from task name
        if self.fileset == None:
            filesetName = ("%s-%s" % (self.wmSpec.name, self.wmSpec.topLevelTaskName))
            if self.block:
                filesetName += "-%s" % self.block
            #TODO: in productin job still need to create the unique fileset name.
            # currently passing the unique fake block name
            self.fileset = Fileset(filesetName)
            self.fileset.create()
        return self.fileset


    def createSubscription(self):
        """
        _createSubscription_
        
        create the wmbs subscription by a given fileset name and workflow name
        """
        if self.subscription == None:
            self.createFilesset()
            self.createWorkflow()
            self.subscription = Subscription(self.fileset, self.workflow,
                                             whitelist = self.wmSpec.whitelist,
                                             blacklist = self.wmSpec.blacklist)
            self.subscription.create()
        return self.subscription

    def addFiles(self, dbsFiles, locations):
        """
        _createFiles_
        
        create wmbs files from given dbs files.
        as well as run lumi update
        """

        if type(dbsFiles) != list:
            dbsFiles = [dbsFiles]
        
        fileset = self.createFilesset()
        for dbsFile in dbsFiles:    
            wmbsFile = File(lfn = dbsFile["LogicalFileName"], 
                            size = dbsFile["FileSize"], 
                            events = dbsFile["NumberOfEvents"], 
                            cksum = dbsFile["Checksum"],
                            parents = dbsFile["ParentList"],
                            locations = Set(locations))
            wmbsFile.create()
            fileset.addFile(wmbsFile)
        fileset.commit()
