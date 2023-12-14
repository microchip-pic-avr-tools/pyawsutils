"""
This module contains helpers for AWS services
"""
import boto3
import botocore

from .pyaws_errors import PyawsError

def create_aws_session(aws_profile='default'):
    """
    Create AWS session

    :param aws_profile: Name of profile to use, defaults to 'default'
    :type aws_profile: str, optional
    :returns: Client to AWS session
    :rtype: botocore session
    :raises PyawsError: If profile can't be found
    """
    try:
        aws_session = boto3.session.Session(profile_name=aws_profile)
    except botocore.exceptions.ProfileNotFound as error:
        if aws_profile == 'default':
            raise PyawsError('AWS profile not found. Please make sure you have the AWS CLI installed and run'
                             ' "aws configure" to setup profile.') from error
        raise PyawsError('AWS profile not found. Please make sure you have the AWS CLI installed and run'
                         ' "aws configure --profile {}" to setup profile.'.format(aws_profile)) from error

    return aws_session

def get_aws_endpoint(aws_session=None, aws_profile='default'):
    """
    Get AWS endpoint

    :param aws_session: Client to AWS session, if None a client will be created on the fly, defaults to None
    :type aws_iot_client: botocore session, optional
    :param aws_profile: Name of profile to use, not used if aws_session is provided, defaults to 'default'
    :type aws_profile: str, optional
    :returns: Endpoint address
    :rtype: str
    """
    if not aws_session:
        aws_session = create_aws_session(aws_profile)

    # Create a client to the AWS IoT service
    aws_iot_client = aws_session.client('iot')

    return aws_iot_client.describe_endpoint(endpointType="iot:Data-ATS").get("endpointAddress")