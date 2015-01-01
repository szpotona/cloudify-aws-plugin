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

# built-in package
import time

# other packages
from boto.ec2 import EC2Connection as EC2
from boto.exception import EC2ResponseError
from boto.exception import BotoServerError

# ctx packages
from cloudify import ctx
from cloudify.exceptions import NonRecoverableError
from cloudify.decorators import operation

# EC2 Instance States
INSTANCE_RUNNING = 16
INSTANCE_TERMINATED = 48
INSTANCE_STOPPED = 80

# Timeouts
CREATION_TIMEOUT = 15 * 60
START_TIMEOUT = 15 * 30
STOP_TIMEOUT = 3 * 60
TERMINATION_TIMEOUT = 3 * 60
CHECK_INTERVAL = 20

# EC2 Method Arguments
RUN_INSTANCES_UNSUPPORTED = {
    'min_count': 1,
    'max_count': 1
}


@operation
def create(**kwargs):
    """ Creates an AWS Instance from an (AMI) image_id and an instance_type.
    """

    arguments = dict()
    arguments['image_id'] = ctx.node.properties['image_id']
    arguments['instance_type'] = ctx.node.properties['instance_type']
    args_to_merge = build_arg_dict(ctx.node.properties['attributes'].copy(),
                                   RUN_INSTANCES_UNSUPPORTED)
    arguments.update(args_to_merge)

    ctx.logger.info('(Node: {0}): Creating instance.'.format(ctx.instance.id))
    ctx.logger.debug("""(Node: {0}): Attempting to create instance.
                        (Image id: {1}. Instance type: {2}.)"""
                     .format(ctx.instance.id, arguments['image_id'],
                             arguments['instance_type']))
    ctx.logger.debug('(Node: {0}): Run instance parameters: {1}.'
                     .format(ctx.instance.id, arguments))

    try:
        reservation = EC2().run_instances(**arguments)
    except EC2ResponseError:
        handle_ec2_error(ctx.instance.id, EC2ResponseError, 'create')
    except BotoServerError:
        handle_ec2_error(ctx.instance.id, BotoServerError, 'create')

    instance_id = reservation.instances[0].id
    ctx.instance.runtime_properties['instance_id'] = instance_id

    if validate_instance_id(reservation.instances[0].id):
        validate_state(reservation.instances[0], INSTANCE_RUNNING,
                       CREATION_TIMEOUT, CHECK_INTERVAL)


@operation
def start(**kwargs):

    instance_id = ctx.instance.runtime_properties['instance_id']

    ctx.logger.info('(Node: {0}): Starting instance.'.format(ctx.instance.id))
    ctx.logger.debug("""(Node: {0}): Attempting to start instance.
                        (Instance id: {1}.)"""
                     .format(ctx.instance.id, instance_id))

    try:
        instances = EC2().start_instances(instance_id)
    except EC2ResponseError:
        handle_ec2_error(ctx.instance.id, EC2ResponseError, 'start')
    except BotoServerError:
        handle_ec2_error(ctx.instance.id, BotoServerError, 'start')

    if validate_instance_id(instances[0].id):
        validate_state(instances[0], INSTANCE_RUNNING,
                       START_TIMEOUT, CHECK_INTERVAL)


@operation
def stop(**kwargs):

    instance_id = ctx.instance.runtime_properties['instance_id']

    ctx.logger.info('(Node: {0}): Stopping instance.'.format(ctx.instance.id))
    ctx.logger.debug('(Node: {0}): Attempting to stop instance.'
                     .format(ctx.instance.id))

    try:
        instances = EC2().stop_instances(instance_id)
    except EC2ResponseError:
        handle_ec2_error(ctx.instance.id, EC2ResponseError, 'stop')
    except BotoServerError:
        handle_ec2_error(ctx.instance.id, BotoServerError, 'stop')

    if validate_instance_id(instances[0].id):
        validate_state(instances[0], INSTANCE_STOPPED,
                       STOP_TIMEOUT, CHECK_INTERVAL)


@operation
def terminate(**kwargs):

    instance_id = ctx.instance.runtime_properties['instance_id']

    ctx.logger.info('(Node: {0}): Terminating instance.'
                    .format(ctx.instance.id))
    ctx.logger.debug('(Node: {0}): Attempting to terminate instance.'
                     .format(ctx.instance.id))

    try:
        instances = EC2().terminate_instances(instance_id)
    except EC2ResponseError:
        handle_ec2_error(ctx.instance.id, EC2ResponseError, 'terminate')
    except BotoServerError:
        handle_ec2_error(ctx.instance.id, BotoServerError, 'terminate')

    if validate_instance_id(instances[0].id):
        validate_state(instances[0], INSTANCE_TERMINATED,
                       TERMINATION_TIMEOUT, CHECK_INTERVAL)


def validate_instance_id(instance_id):

    try:
        instance = EC2().get_all_instances(instance_id)
    except EC2ResponseError:
        handle_ec2_error(ctx.instance.id, EC2ResponseError, 'validate')
    except BotoServerError:
        handle_ec2_error(ctx.instance.id, BotoServerError, 'create')

    if instance:
        return True
    else:
        ctx.logger.error('(Node: {0}): Unable to validate instance ID: {1}.'
                         .format(ctx.instance.id, instance_id))
        raise NonRecoverableError("""(Node: {0}):
                                     Unable to validate instance ID: {1}."""
                                  .format(ctx.instance.id, instance_id))


def validate_state(instance, state, timeout_length, check_interval):

    ctx.logger.debug("""(Node: {0}): Attempting state validation:
                       instance id: {0}, state: {1}, timeout length: {2},
                       check interval: {3}.""".format(instance.id, state,
                                                      timeout_length,
                                                      check_interval))

    timeout = time.time() + timeout_length

    while True:
        if state == _get_instance_state(instance):
            ctx.logger.info("""(Node: {0}):
                               Instance state validated: instance {0}."""
                            .format(instance.state))
            return True
        elif time.time() > timeout:
            ctx.logger.error("""(Node: {0}): Timedout during instance state
                                validation: instance: {1}, timeout length: {2},
                                check interval: {3}."""
                             .format(ctx.instance.node, instance.id,
                                     timeout_length, check_interval))
            raise NonRecoverableError("""(Node: {0}): Timed out during instance
                                         state validation: instance: {1},
                                         timeout length: {2},
                                         check interval: {3}."""
                                      .format(ctx.instance.id,
                                              TERMINATION_TIMEOUT))
            return False

        time.sleep(check_interval)


def _get_instance_state(instance):
    """

    :param instance:
    :return:
    """

    state = instance.update()
    ctx.logger.debug('(Node: {0}): Instance state is {1}.'
                     .format(ctx.instance.id, state))
    return instance.state_code


def handle_ec2_error(instance, ec2_error, action):

    ctx.logger.error("""(Node: {0}): Error. Failed to {1} instance:
                        API returned: {2}.""" .format(ctx.instance.id, action,
                                                      ec2_error.body))
    raise NonRecoverableError("""(Node: {0}): Error. Failed to {1} instance:
                                 API returned: {2}.""".format(ctx.instance.id,
                                                              action,
                                                              ec2_error.body))


def build_arg_dict(user_supplied, unsupported):

    arguments = {}
    for pair in user_supplied.items():
        arguments[pair[0]] = pair[1]
    for pair in unsupported.items():
        arguments[pair[0]] = pair[1]
    return arguments


@operation
def creation_validation(**kwargs):
    instance_id = ctx.instance.runtime_properties['instance_id']
    state = INSTANCE_RUNNING
    timeout_length = CREATION_TIMEOUT

    if validate_state(instance_id, state, timeout_length, CHECK_INTERVAL):
        ctx.logger.debug('Instance is running.')
    else:
        raise NonRecoverableError('Instance not running.')
