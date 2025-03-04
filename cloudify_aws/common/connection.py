# Copyright (c) 2018 Cloudify Platform Ltd. All rights reserved
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""
    Connection
    ~~~~~~~~~~
    AWS connection
"""
# Third party imports
import boto3
from botocore.config import Config

# Local imports
from .utils import desecretize_client_config
from cloudify_aws.common.constants import AWS_CONFIG_PROPERTY

# pylint: disable=R0903


class Boto3Connection(object):
    '''
        Provides a sugared connection to an AWS service

    :param `cloudify.context.NodeContext` node: A Cloudify node
    :param dict aws_config: AWS connection configuration overrides
    '''
    def __init__(self, node, aws_config=None):
        aws_config_whitelist = [
            'aws_access_key_id',
            'aws_secret_access_key',
            'region_name']
        aws_config_options = [
            'aws_session_token',
            'api_version']

        config_from_props = node.properties.get(AWS_CONFIG_PROPERTY, dict())
        # Get additional config from node configuration.
        additional_config = config_from_props.pop('additional_config', None)

        self.aws_config = desecretize_client_config(config_from_props)
        # Merge user-provided AWS config with generated config
        if aws_config:
            self.aws_config.update(aws_config)

        # Prepare region name for Boto
        self.aws_config['region_name'] = self.aws_config.get('region_name')

        # This it check if "aws_config" contains "endpoint_url" or not
        for option in aws_config_options:
            if self.aws_config.get(option):
                aws_config_whitelist.append(option)

        # Delete all non-whitelisted keys
        self.aws_config = {k: v for k, v in self.aws_config.items()
                           if k in aws_config_whitelist}

        # Add additional config after whitelist filter.
        if additional_config and isinstance(additional_config, dict):
            self.aws_config['config'] = Config(**additional_config)

    def client(self, service_name):
        '''
            Builds an AWS connection client

        :param str service_name: A Boto3 service name
        :returns: An AWS service Boto3 client
        :raises: :exc:`cloudify.exceptions.NonRecoverableError`
        '''
        resource = boto3.client(service_name, **self.aws_config)
        return resource
