"""
.. module: historical.tests.test_s3
    :platform: Unix
    :copyright: (c) 2017 by Netflix Inc., see AUTHORS for more
    :license: Apache, see LICENSE for more details.
.. author:: Kevin Glisson <kglisson@netflix.com>
.. author:: Mike Grima <mgrima@netflix.com>
"""
import os
import pytest
from datetime import datetime

import boto3

from moto.dynamodb2 import mock_dynamodb2
from moto.kinesis import mock_kinesis
from moto.s3 import mock_s3
from moto.iam import mock_iam
from moto.sts import mock_sts
from moto.ec2 import mock_ec2


@pytest.fixture(scope='function')
def s3():
    with mock_s3():
        yield boto3.client('s3', region_name='us-east-1')


@pytest.fixture(scope='function')
def ec2():
    with mock_ec2():
        yield boto3.client('ec2', region_name='us-east-1')


@pytest.fixture(scope='function')
def sts():
    with mock_sts():
        yield boto3.client('sts', region_name='us-east-1')


@pytest.fixture(scope='function')
def iam():
    with mock_iam():
        yield boto3.client('iam', region_name='us-east-1')


@pytest.fixture(scope='function')
def dynamodb():
    with mock_dynamodb2():
        yield boto3.client('dynamodb', region_name='us-east-1')


@pytest.fixture(scope='function')
def swag_accounts(s3):
    from swag_client.backend import SWAGManager
    from swag_client.util import parse_swag_config_options

    bucket_name = 'SWAG'
    data_file = 'accounts.json'
    region = 'us-east-1'
    owner = 'third-party'

    s3.create_bucket(Bucket=bucket_name)
    os.environ['SWAG_BUCKET'] = bucket_name
    os.environ['SWAG_DATA_FILE'] = data_file
    os.environ['SWAG_REGION'] = region
    os.environ['SWAG_OWNER'] = owner

    swag_opts = {
        'swag.type': 's3',
        'swag.bucket_name': bucket_name,
        'swag.data_file': data_file,
        'swag.region': region,
        'swag.cache_expires': 0
    }

    swag = SWAGManager(**parse_swag_config_options(swag_opts))

    account = {
        'aliases': ['test'],
        'contacts': ['admins@test.net'],
        'description': 'LOL, Test account',
        'email': 'testaccount@test.net',
        'environment': 'test',
        'id': '012345678910',
        'name': 'testaccount',
        'owner': 'third-party',
        'provider': 'aws',
        'sensitive': False,
        'services': [
            {
                'name': 'historical',
                'status': [
                    {
                        'region': 'all',
                        'enabled': True
                    }
                ]
            }
        ]
    }

    swag.create(account)


@pytest.fixture(scope='function')
def historical_role(iam, sts):
    iam.create_role(RoleName='historicalrole', AssumeRolePolicyDocument='{}')
    os.environ['HISTORICAL_ROLE'] = 'historicalrole'


@pytest.fixture(scope='function')
def historical_kinesis():
    with mock_kinesis():
        client = boto3.client('kinesis', region_name='us-east-1')
        client.create_stream(StreamName='historicalstream', ShardCount=1)
        os.environ['HISTORICAL_STREAM'] = 'historicalstream'
        yield client


@pytest.fixture(scope='function')
def buckets(s3):
    # Create buckets:
    for i in range(0, 50):
        s3.create_bucket(Bucket='testbucket{}'.format(i))
        s3.put_bucket_tagging(
            Bucket='testbucket{}'.format(i),
            Tagging={
                'TagSet': [
                    {
                        'Key': 'theBucketName',
                        'Value': 'testbucket{}'.format(i)
                    }
                ]
            }
        )
        s3.put_bucket_lifecycle_configuration(Bucket='testbucket{}'.format(i), LifecycleConfiguration={
            'Rules': [
                {
                    'Expiration': {
                        'Date': datetime(2015, 1, 1),
                        'Days': 123,
                        'ExpiredObjectDeleteMarker': True | False
                    },
                    'ID': 'string',
                    'Prefix': 'string',
                    'Filter': {
                        'Prefix': 'string',
                        'Tag': {
                            'Key': 'string',
                            'Value': 'string'
                        },
                        'And': {
                            'Prefix': 'string',
                            'Tags': [
                                {
                                    'Key': 'string',
                                    'Value': 'string'
                                },
                            ]
                        }
                    },
                    'Status': 'Enabled',
                    'Transitions': [
                        {
                            'Date': datetime(2015, 1, 1),
                            'Days': 123,
                            'StorageClass': 'GLACIER'
                        },
                    ],
                    'NoncurrentVersionTransitions': [
                        {
                            'NoncurrentDays': 123,
                            'StorageClass': 'GLACIER'
                        },
                    ],
                    'NoncurrentVersionExpiration': {
                        'NoncurrentDays': 123
                    },
                    'AbortIncompleteMultipartUpload': {
                        'DaysAfterInitiation': 123
                    }
                }
            ]
        })


@pytest.fixture(scope='function')
def security_groups(ec2):
    """Creates security groups."""
    yield ec2.create_security_group(
        Description='test security group',
        GroupName='test',
        VpcId='vpc-test'
    )


@pytest.fixture(scope='function')
def mock_lambda_environment():
    os.environ['SENTRY_ENABLED'] = 'f'


@pytest.fixture(scope='function')
def current_security_group_table():
    from historical.security_group.models import CurrentSecurityGroupModel
    mock_dynamodb2().start()
    yield CurrentSecurityGroupModel.create_table(read_capacity_units=1, write_capacity_units=1, wait=True)
    mock_dynamodb2().stop()


@pytest.fixture(scope='function')
def durable_security_group_table():
    from historical.security_group.models import DurableSecurityGroupModel
    mock_dynamodb2().start()
    yield DurableSecurityGroupModel.create_table(read_capacity_units=1, write_capacity_units=1, wait=True)
    mock_dynamodb2().stop()


@pytest.fixture(scope='function')
def current_s3_table(dynamodb):
    from historical.s3.models import CurrentS3Model
    yield CurrentS3Model.create_table(read_capacity_units=1, write_capacity_units=1, wait=True)


@pytest.fixture(scope='function')
def durable_s3_table(dynamodb):
    from historical.s3.models import DurableS3Model
    yield DurableS3Model.create_table(read_capacity_units=1, write_capacity_units=1, wait=True)
