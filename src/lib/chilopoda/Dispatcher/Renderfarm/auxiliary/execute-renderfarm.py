import os
import sys
import json
import argparse
from glob import glob
from collections import OrderedDict
from chilopoda.Dispatcher import Dispatcher
from chilopoda.Crawler import Crawler
from chilopoda.TaskHolder import TaskHolder

def __runCollapsed(data, taskHolder, dataJsonFile):
    """
    Execute a collapsed job.
    """
    taskInputFilePaths = []

    # we use dataJsonFile to find auxiliary files used by
    # the dispatcher
    name, ext = os.path.splitext(dataJsonFile)

    # checking if the job has been already processed. This happens
    # when a collapsed job dispatches expanded jobs on the farm. The
    # dispatched jobs get added as dependencies of the collapsed
    # job itself. Therefore, when the dependencies are completed
    # and the job gets resumed (restarted). We want to avoid the job to
    # execute itself again by just returning it right away.
    jobProcessedFilePath = "{}_jobProcessed".format(name)
    if os.path.exists(jobProcessedFilePath):
        sys.stdout.write("Job has been already processed, skipping it.\n")
        return
    # otherwise we "touch" a file used in the future to tell the job has been
    # already processed
    else:
        open(jobProcessedFilePath, 'a').close()

    # looking for its own job id on the farm, this information
    # is going to be used to include the expanded jobs
    # as dependency of the job itself.
    jobIdFilePath = "{}_jobId.{ext}".format(
        name,
        ext=ext[1:]
    )

    mainJobId = None
    if os.path.exists(jobIdFilePath):
        with open(jobIdFilePath) as jsonFile:
            mainJobId = json.load(jsonFile)["id"]

    # looking for a task that has been chunkfied on the farm
    if len(data['taskInputFilePaths']) == 1 and not os.path.exists(data['taskInputFilePaths'][0]):
        nameParts = os.path.splitext(data['taskInputFilePaths'][0])

        taskInputFilePaths = glob(
            "{}_range_*_*.{ext}".format(nameParts[0], ext=nameParts[1][1:])
        )

        # since the range is padded by sorting them it is going to
        # provide the proper order that the crawlers should be loaded
        taskInputFilePaths.sort()
    else:
        taskInputFilePaths = data['taskInputFilePaths']

    # loading input crawlers
    crawlers = []
    for taskInputFilePath in taskInputFilePaths:
        with open(taskInputFilePath) as jsonFile:
            serializedCrawlers = json.load(jsonFile)
            crawlers += list(map(lambda x: Crawler.createFromJson(x), serializedCrawlers))

    dispatcher = Dispatcher.createFromJson(data['dispatcher'])
    dispatchedIds = dispatcher.dispatch(
        taskHolder,
        crawlers
    )

    # since this job can be used as dependency of other jobs
    # we need to include the dispatched jobs as dependencies
    # of itself. Also, the implementation of "extendDependencyIds"
    # may need to mark the mainJobId as pending status again
    # in case your renderfarm manager does not do that
    # automatically. In case your renderfarm manager executes the
    # main job again (when all the new dependencies are completed)
    # the dispatcher is going to ignore the second execution
    # automatically.
    if mainJobId is not None:
        dispatcher.extendDependencyIds(
            mainJobId,
            dispatchedIds
        )

def __runExpanded(data, taskHolder, rangeStart, rangeEnd):
    """
    Execute an expanded job.
    """
    taskResultFilePath = data['taskResultFilePath']

    # in case the range has been specified
    if rangeStart is not None:

        # since a range has been assigned we need to modify the result file name
        # to include the range information. This can only be done at this point
        # since execute-renderfarm is called directly by the renderfarm
        # manager itself to split the job in chunks (when chunkifyOnTheFarm
        # option is enabled in the dispatcher)
        nameParts = os.path.splitext(taskResultFilePath)
        taskResultFilePath = "{}_range_{}_{}.{ext}".format(
            nameParts[0],
            str(rangeStart).zfill(10),
            str(rangeEnd).zfill(10),
            ext=nameParts[1][1:]
        )

        # collecting all crawlers so we can re-assign only the ones that belong
        # to the range
        task = taskHolder.task()
        crawlers = OrderedDict()
        for crawler in task.crawlers():
            crawlers[crawler] = task.target(crawler)

        # including only the crawlers from the specific range
        task.clear()
        for crawler in list(crawlers.keys())[rangeStart: rangeEnd + 1]:
            filePath = crawlers[crawler]
            task.add(
                crawler,
                filePath
            )

    outputCrawlers = taskHolder.run()

    # writing resulted crawlers
    with open(taskResultFilePath, 'w') as jsonFile:
        data = list(map(lambda x: x.toJson(), outputCrawlers))
        json.dump(
            data,
            jsonFile,
            indent=4
        )

def __run(dataJsonFile, rangeStart=None, rangeEnd=None):
    """
    Execute the taskHolder.
    """
    data = {}
    with open(dataJsonFile) as jsonFile:
        data = json.load(jsonFile)

    # loading task holder
    taskHolder = TaskHolder.createFromJson(data['taskHolder'])

    if data['jobType'] == "collapsed":
        __runCollapsed(
            data,
            taskHolder,
            dataJsonFile
        )

    elif data['jobType'] == "expanded":
        __runExpanded(
            data,
            taskHolder,
            rangeStart,
            rangeEnd
        )

    else:
        raise Exception(
            "Invalid execution type: {}".format(data['jobType'])
        )


# command-line interface
parser = argparse.ArgumentParser()

parser.add_argument(
    'data',
    metavar='data',
    type=str,
    help='json file containing the data that should be executed'
)

parser.add_argument(
    '--range-start',
    type=int,
    action="store",
    help='In case the task has been chunkfied on the farm, tells the context about the start crawler index'
)

parser.add_argument(
    '--range-end',
    type=int,
    action="store",
    help='In case the task has been chunkfied on the farm, tells the context about the end crawler index'
)

# executing it
if __name__ == "__main__":
    args = parser.parse_args()

    __run(
        args.data,
        args.range_start,
        args.range_end
    )
