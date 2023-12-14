"""
AWS Lambda Function utility
"""

#-- Import modules
from logging import getLogger
from venv import create

from .aws_services import create_aws_session

def update_lambda_function(zip_file, stackname, aws_profile='default'):
    """
    Update lambda function with ZIP deployment package

    :param zip_file: full path to zip file to use
    :type zip_file: str
    :param stackname: name of stack to update
    :type stackname: str
    :param aws_profile: Name of AWS profile to use, defaults to 'default'
    :type aws_profile: str, optional
    """
    logger = getLogger(__name__)
    with open(zip_file, mode='rb') as file: # b is important -> binary
        zip_data = file.read()

    # Update lambda function
    aws_session = create_aws_session(aws_profile=aws_profile)
    client = aws_session.client('lambda')

    # List functions. Find correct function / stack to update
    myfunctions_list = client.list_functions()["Functions"]

    myfunction_name = "NULL"
    for myfunction in myfunctions_list:
        if stackname in myfunction["FunctionName"]:
            myfunction_name = myfunction["FunctionName"]

    #Update function code
    logger.info("")
    if myfunction_name != "NULL":
        logger.info("Updating lambda function %s", myfunction_name)
        client.update_function_code(
            FunctionName=myfunction_name,
            ZipFile=zip_data,
            Publish=True,
        )
    else:
        logger.info("No function to update in this stack: %s", stackname)
