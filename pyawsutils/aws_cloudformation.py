"""
Methods to use AWS Cloudformation
"""

#-- Import modules
import time
from os import path
from logging import getLogger
import boto3

from . import aws_lambda
from .pyaws_errors import PyawsError

STATUS_SUCCESS = 0
STATUS_FAILURE = 1

# The following is a legacy endpoint and should not be explicitly used in new applications.
MCHP_SANDBOX_LEGACY_ENDPOINT = "a1gqt8sttiign3.iot.us-east-2.amazonaws.com"
# The ATS endpoint should be used for new applications (Cellular, for now).
# See https://www.amazontrust.com/repository/
MCHP_SANDBOX_ATS_ENDPOINT = "a1gqt8sttiign3-ats.iot.us-east-2.amazonaws.com"
# Default AWS endpoint, use to force-feed change to unaware applications
MCHP_SANDBOX_ENDPOINT = MCHP_SANDBOX_LEGACY_ENDPOINT

CLOUDFORMATION_TEMPLATE_NAME = "custom_cf_template.json"
CLOUDFORMATION_STACK_NAME = "MCHPStack"
LAMBDA_ZIPPACK_NAME = "custom_lambdapack.zip"
CLOUDFORMATION_FOLDER = "aws_cf"

def setup_aws_jitr_account(force):
    """
    Setup AWS account for JITR, using Cloudformation and uploading Lambda pack with JITR code

    :param force: force stack creation again if it already exists
    :type force: boolean
    """
    here = path.abspath(path.dirname(__file__))
    aws_cf_folder = path.join(here, CLOUDFORMATION_FOLDER)

    create_cloudformation_stack(
        path.join(aws_cf_folder, CLOUDFORMATION_TEMPLATE_NAME), CLOUDFORMATION_STACK_NAME,
        path.join(aws_cf_folder, LAMBDA_ZIPPACK_NAME), force)

    return STATUS_SUCCESS


def check_status(cf_client, stack_name):
    """
    Check status of Cloudformation stacks

    :param cf_client: cloud formation client
    :type cf_client: boto3 client object
    :param stack_name: name of stack to check
    :type stack_name: str

    :returns: status: "CREATE_COMPLETE", "IN_PROGRESS" or "STACK_DELETED"
    :rtype: str
    """
    logger = getLogger(__name__)
    stacks = cf_client.describe_stacks(StackName=stack_name)["Stacks"]
    stack0 = stacks[0]
    cur_status = stack0["StackStatus"]
    logger.debug("Current status of stack %s: %s", stack0["StackName"], cur_status)
    log_count = 0
    for _ in range(1, 9999):
        if "IN_PROGRESS" in cur_status:
            if log_count == 0:
                logger.info("Waiting for status update, this might take some time...")
            elif log_count % 10 == 0:
                # To avoid flooding the output with status messages only log a message at every 10th check
                logger.info("Still waiting for status update...")
            log_count += 1
            # Wait a bit before checking status again
            time.sleep(1)

            try:
                stacks = cf_client.describe_stacks(StackName=stack_name)["Stacks"]
            except:
                logger.debug("Stack %s no longer exists", stack0["StackName"])
                cur_status = "STACK_DELETED"
                break

            stack0 = stacks[0]
            if stack0["StackStatus"] != cur_status:
                cur_status = stack0["StackStatus"]
                logger.debug("Updated status of stack %s: %s", stack0["StackName"], cur_status)
        else:
            break

    return cur_status


def create_cloudformation_stack(pc_template_file, stackname, zipname="", force=False):
    """
    Create Cloudformation stack based on JSON template
    Update lambda function with zip deployment package
    """
    logger = getLogger(__name__)
    logger.info("Setting up custom account...")
    #Checking endpoint
    iot_client = boto3.client('iot')
    response = iot_client.describe_endpoint()
    aws_endpoint_address = response['endpointAddress']
    logger.info("AWS endpoint : %s", aws_endpoint_address)
    #stop operation if sandbox account
    if aws_endpoint_address == MCHP_SANDBOX_ENDPOINT:
        raise PyawsError("Please don't use the Microchip Sandbox account for custom setup")

    json_data = open(pc_template_file).read()

    #Create cloudformation client
    cf_client = boto3.client('cloudformation')
    #-- Store parameters from file into local variables
    stack_name = stackname

    #-- Check if this stack name already exists
    stack_list = cf_client.describe_stacks()["Stacks"]
    stack_exists = False
    for stack in stack_list:
        if stack_name == stack["StackName"]:
            logger.debug("Stack %s already exists.", stack_name)
            stack_exists = True

    #return from function if stack already exist and not forced
    if stack_exists and not force:
        logger.info("Using existing Stack %s", stack_name)
        return

    #-- If the stack already exists then delete it first
    if stack_exists and force:
        logger.info("Deleting current stack: %s", stack_name)
        try:
            cf_client.delete_stack(StackName=stack_name)
        except:
            raise PyawsError("Could not delete/create new stack on account."
                             "Does the AWS account have the CloudFormation permission?")

        #-- Check the status of the stack deletion
        check_status(cf_client, stack_name)

    logger.info("Creating stack: %s", stack_name)

    try:
        response = cf_client.create_stack(StackName=stack_name, DisableRollback=True,
                                          TemplateBody=json_data,
                                          Capabilities=["CAPABILITY_NAMED_IAM"])
    except:
        raise PyawsError("Could not create new stack on account."
                         " Does the AWS account have the CloudFormation permission?")

    logger.debug("Output from API call: ")
    logger.debug(response)

    #-- Check the status of the stack creation
    cur_status = check_status(cf_client, stack_name)
    if cur_status == "CREATE_COMPLETE":
        logger.info("Stack (%s) created successfully.", stack_name)
    else:
        raise PyawsError("Failed to create stack {}".format(stack_name))

    #Update function with correct ZIP deployment pacakge
    if zipname != "":
        aws_lambda.update_lambda_function(zipname, stackname)

def jitr_cli_handler():
    """
    Entry point for JITR command of CLI
    """
    setup_aws_jitr_account(force=True)
    return STATUS_SUCCESS
