########
# Copyright (c) 2014 GigaSpaces Technologies Ltd. All rights reserved
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
#    * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    * See the License for the specific language governing permissions and
#    * limitations under the License.

# Boto Imports
from boto.exception import EC2ResponseError
from boto.exception import BotoServerError
from boto.exception import BotoClientError

# Cloudify imports
from cloudify import ctx
from cloudify.exceptions import NonRecoverableError
from cloudify.decorators import operation
from ec2 import utils
from ec2 import connection


@operation
def create(**kwargs):
    """ This will create the key pair within the region you are currently
        connected to.
    """
    ec2_client = connection.EC2ConnectionClient().client()
    key_pair_name = ctx.node.properties['resource_id']
    ctx.logger.info('Creating key pair.')

    try:
        kp = ec2_client.create_key_pair(key_pair_name)
    except (EC2ResponseError, BotoServerError, BotoClientError) as e:
        raise NonRecoverableError('Key pair not created. '
                                  'API returned: {0}'.format(str(e)))

    ctx.logger.info('Created key pair: {0}.'.format(kp.name))
    ctx.instance.runtime_properties['aws_resource_id'] = kp.name

    utils.save_key_pair(kp, ctx=ctx)


@operation
def delete(**kwargs):
    """ This will delete the key pair that you specified in the blueprint
        when this lifecycle operation is called.
    """
    ec2_client = connection.EC2ConnectionClient().client()
    key_pair_name = ctx.instance.runtime_properties['aws_resource_id']
    ctx.logger.info('Deleting the keypair.')

    try:
        ec2_client.delete_key_pair(key_pair_name)
    except (EC2ResponseError, BotoServerError) as e:
        raise NonRecoverableError('Error response on key pair delete. '
                                  'API returned: {0}'.format(str(e)))

    ctx.logger.info('Deleted key pair: {0}.'.format(key_pair_name))
    utils.delete_key_pair(key_pair_name, ctx=ctx)
    ctx.instance.runtime_properties.pop('aws_resource_id', None)


@operation
def creation_validation(**kwargs):
    ec2_client = connection.EC2ConnectionClient().client()
    ctx.logger.info('Validating that the keypair '
                    'was created in your account.')
    key_pair_name = ctx.instance.runtime_properties['aws_resource_id']

    try:
        ec2_client.get_key_pair(key_pair_name)
    except (EC2ResponseError, BotoServerError) as e:
        raise NonRecoverableError('Unable to validate that Key Pair exists. '
                                  'API returned: {0}'.format(str(e)))

    ctx.logger.info('Validated key pair.')
