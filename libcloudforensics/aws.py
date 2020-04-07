# -*- coding: utf-8 -*-
# Copyright 2020 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Library for incident response operations on AWS EC2."""
import binascii
import datetime
import logging
import os
import re

import boto3

log = logging.getLogger()

EC2_SERVICE = 'ec2'
ACCOUNT_SERVICE = 'sts'
UBUNTU_1804_AMI = 'ami-0013b3aa57f8a4331'
AWS_PATH = os.path.expanduser('~/.aws/')
RETRY_MAX = 10
REGEX_TAG_VALUE = re.compile('^.{1,255}$')


def CreateSession():
  """Create an AWS session API service.

  Returns:
    boto3.Session: An AWS session object.
  """
  # Create a default session with credentials stored in ~/.aws/credentials
  # https://boto3.amazonaws.com/v1/documentation/api/latest/guide
  # /configuration.html
  return boto3.session.Session()


class AwsAccount:
  """Class representing an AWS account.

  Attributes:
    default_availability_zone (str): Default zone within the region to create
    new resources in.
  """
  def __init__(self, default_availability_zone):
    self.default_availability_zone = default_availability_zone
    # The region is given by the zone minus the last letter
    # https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/using-regions
    # -availability-zones.html#using-regions-availability-zones-describe
    self.default_region = self.default_availability_zone[:-1]

  def ClientApi(self, service, region=None):
    """Create an AWS client object.

    Attributes:
      service (str): The AWS service to use.
      region (str): The region is which to create new resources in.

    Returns:
      boto3.Session.Client: An AWS EC2 client object.
    """
    if region:
      return CreateSession().client(
          service_name=service, region_name=region
      )
    return CreateSession().client(
        service_name=service, region_name=self.default_region
    )

  def ResourceApi(self, service, region=None):
    """Create an AWS resource object.

    Attributes:
      service (str): The AWS service to use.
      region (str): The region is which to create new resources in.

    Returns:
      boto3.Session.Resource: An AWS EC2 resource object.
    """
    if region:
      return CreateSession().resource(
          service_name=service, region_name=region
      )
    return CreateSession().resource(
        service_name=service, region_name=self.default_region
    )

  def ListInstances(self, region=None, filters=None):
    """List instances of an AWS account.

    Attributes:
      region (str): The region from which to list instances.
      filters (list(dict)): Filters for the query.

    Returns:
      dict: Dictionary with name and metadata for each instance.

    Example usage:
      ListInstances(region='us-east-1', filters=[
        dict(Name='instance-id', Values=['a-particular-instance-id'])
      ])
    """
    if not filters:
      filters = []

    instances = dict()
    have_all_tokens = False
    next_token = None

    while not have_all_tokens:
      if next_token:
        response = self.ClientApi(
            EC2_SERVICE, region=region).describe_instances(
                Filters=filters,
                NextToken=next_token)
      else:
        response = self.ClientApi(
            EC2_SERVICE, region=region).describe_instances(
                Filters=filters)

      for reservation in response["Reservations"]:
        for instance in reservation["Instances"]:
          instance_name = None
          if instance.get('Tags'):
            for tag in instance['Tags']:
              instance_name = tag.get('Value') if tag.get('Key') == 'Name' \
                else None
              if instance_name is not None:
                break
          # Terminated instances are filtered out
          if instance['State']['Name'] != 'terminated':
            instance_info = dict(region=self.default_region,
                                 zone=instance['Placement']['AvailabilityZone'])
            if instance_name:
              instance_info.update(name=instance_name)
            instances[instance['InstanceId']] = instance_info

      next_token = response.get('NextToken')
      if not next_token:
        have_all_tokens = True

    return instances

  def ListVolumes(self, region=None, filters=None):
    """List volumes of an AWS account.

    Attributes:
      region (str): The region from which to list the volumes.
      filters (list(dict)): Filter for the query.

    Returns:
      dict: Dictionary with name and metadata for each volume.

    Example usage:
      # List volumes attached to the instance 'a-particular-instance-id'
      ListVolumes(filters=[
        dict(Name='attachment.instance-id', Values=['a-particular-instance-id'])
      ])
    """
    if not filters:
      filters = []

    volumes = dict()
    have_all_tokens = False
    next_token = None

    while not have_all_tokens:
      if next_token:
        response = self.ClientApi(
            EC2_SERVICE, region=region).describe_volumes(
                Filters=filters,
                NextToken=next_token
            )
      else:
        response = self.ClientApi(
            EC2_SERVICE, region=region).describe_volumes(
                Filters=filters)

      for volume in response['Volumes']:
        volume_name = None
        if volume.get('Tags'):
          for tag in volume['Tags']:
            volume_name = tag.get('Value') if tag.get('Key') == 'Name' \
              else None
            if volume_name is not None:
              break

        volume_info = dict(region=self.default_region,
                           zone=volume['AvailabilityZone'])
        if volume_name:
          volume_info.update(name=volume_name)
        if len(volume['Attachments']) > 0:
          volume_info.update(device=volume['Attachments'][0]['Device'])

        volumes[volume['VolumeId']] = volume_info

      next_token = response.get('NextToken')
      if not next_token:
        have_all_tokens = True

    return volumes

  def GetInstance(self, instance_name_or_id, region=None):
    """Get an instance from an AWS account by its ID or its name tag.

    Args:
      instance_name_or_id (str): The instance to get. This can be the
      instance id or a name that is assigned to the instance as a Tag.
      region (str): The region to look the instance in.

    Returns:
      AwsInstance: An Amazon EC2 Instance object.

    Raises:
      RuntimeError: If instance does not exist.
    """
    aws_instance = None
    try:
      aws_instance = self.__GetInstanceById(instance_name_or_id, region=region)
    except RuntimeError as exception:
      e = exception
    if not aws_instance:
      try:
        aws_instance = self.__GetInstanceByName(
            instance_name_or_id, region=region)
      except RuntimeError as exception:
        e = exception
    if not aws_instance:
      raise RuntimeError(e)
    return aws_instance

  def GetVolume(self, volume_name_or_id, region=None):
    """Get a volume from an AWS account by its ID or its name tag.

    Args:
      volume_name_or_id (str): The volume to get. This can be the volume id or a
      name that is assigned to the volume as a Tag.
      region (str): The region to look the volume in.

    Returns:
      AwsVolume: An Amazon EC2 Volume object.

    Raises:
      RuntimeError: If volume does not exist.
    """
    aws_volume = None
    try:
      aws_volume = self.__GetVolumeById(volume_name_or_id, region=region)
    except RuntimeError as exception:
      e = exception
    if not aws_volume:
      try:
        aws_volume = self.__GetVolumeByName(volume_name_or_id, region=region)
      except RuntimeError as exception:
        e = exception
    if not aws_volume:
      raise RuntimeError(e)
    return aws_volume

  def CreateVolumeFromSnapshot(
      self, snapshot, volume_name=None, volume_name_prefix=''):
    """Create a new volume based on a snapshot.

    Args:
      snapshot (AwsSnapshot): Snapshot to use.
      volume_name (str): Optional string to use as new volume name.
      volume_name_prefix (str): Optional string to prefix the volume name with.

    Returns:
      AwsVolume: An AWS EBS Volume.

    Raises:
      ValueError: If the volume name does not comply with the RegEx.
      RuntimeError: If the volume could not be created.
    """

    if not volume_name:
      volume_name = self._GenerateVolumeName(
          snapshot, volume_name_prefix=volume_name_prefix)

    if not REGEX_TAG_VALUE.match(volume_name):
      raise ValueError('Error: volume name {0:s} does not comply with '
                       '{1:s}'.format(volume_name, REGEX_TAG_VALUE.pattern))

    client = self.ClientApi(EC2_SERVICE)
    try:
      volume = client.create_volume(
          AvailabilityZone=snapshot.availability_zone,
          SnapshotId=snapshot.snapshot_id,
          TagSpecifications=[GetTagForResourceType('volume', volume_name)]
      )
      volume_id = volume['VolumeId']
      zone = volume['AvailabilityZone']
      # Wait for volume creation completion
      client.get_waiter('volume_available').wait(VolumeIds=[volume_id])
    except client.exceptions.ClientError as exception:
      raise RuntimeError('Error: could not create volume {0:s} from snapshot '
                         '{1:s}: {2:s}'.format(
                             volume_name, snapshot.name, str(exception)))

    return AwsVolume(volume_id, self, self.default_region, zone,
                     name=volume_name)

  def _GenerateVolumeName(self, snapshot, volume_name_prefix=None):
    """Generate a new volume name given a volume's snapshot.

    Args:
      snapshot (AwsSnapshot): A volume's Snapshot.
      volume_name_prefix (str): An optional prefix for the volume name.

    Returns:
      str: A name for the volume.

    Raises:
      ValueError: if the volume name does not comply with the RegEx.
    """

    # Max length of tag values in AWS is 255 characters
    user_id = self.ClientApi(ACCOUNT_SERVICE).get_caller_identity()\
      .get('UserId', '')
    volume_id = user_id + snapshot.volume.volume_id
    volume_id_crc32 = '{0:08x}'.format(
        binascii.crc32(volume_id.encode()) & 0xffffffff)
    truncate_at = 255 - len(volume_id_crc32) - len('-copy') - 1
    if volume_name_prefix:
      volume_name_prefix += '-'
      if len(volume_name_prefix) > truncate_at:
        # The volume name prefix is too long
        volume_name_prefix = volume_name_prefix[:truncate_at]
      truncate_at -= len(volume_name_prefix)
      volume_name = '{0:s}{1:s}-{2:s}-copy'.format(
          volume_name_prefix, snapshot.name[:truncate_at], volume_id_crc32)
    else:
      volume_name = '{0:s}-{1:s}-copy'.format(
          snapshot.name[:truncate_at], volume_id_crc32)

    return volume_name

  def __GetInstanceById(self, instance_id, region=None):
    """Get an instance from an AWS account by its ID.

    Args:
      instance_id (str): The instance id.
      region (str): The region to look the instance in.

    Returns:
      AwsInstance: An Amazon EC2 Instance object.

    Raises:
      RuntimeError: If instance does not exist.
    """
    instances = self.ListInstances(region=region)
    instance = instances.get(instance_id)
    if not instance:
      error_msg = 'Instance {0:s} was not found in AWS account'.format(
          instance_id)
      raise RuntimeError(error_msg)

    if not region:
      region = self.default_region

    zone = instance['zone']

    return AwsInstance(self, instance_id, region, zone)

  def __GetInstanceByName(self, instance_name, region=None):
    """Get an instance from an AWS account by its name tag.

    Args:
      instance_name (str): The instance name tag.
      region (str): The region to look the instance in.

    Returns:
      AwsInstance: An Amazon EC2 Instance object.

    Raises:
      RuntimeError: If instance does not exist, or if multiple instances have
      the same name tag.
    """
    instance_id = None
    count = 0
    instances = self.ListInstances(region=region)
    for key in instances:
      if instances[key].get('name') == instance_name:
        instance_id = key
        count += 1

    if count == 0:
      error_msg = 'Instance {0:s} was not found in AWS account'.format(
          instance_name)
      raise RuntimeError(error_msg)
    if count > 1:
      error_msg = 'Multiple instances with tag name {0:s} were found in the ' \
                  'AWS account. Please look-up the instance by its unique ' \
                  'AWS instance-ID instead'.format(instance_name)
      raise RuntimeError(error_msg)

    if not region:
      region = self.default_region

    zone = instances[instance_id]['zone']

    return AwsInstance(self, instance_id, region,
                       zone, name=instance_name)

  def __GetVolumeById(self, volume_id, region=None):
    """Get a volume from an AWS account by its ID.

    Args:
      volume_id (str): The volume id.
      region (str): The region to look the volume in.

    Returns:
      AwsVolume: An Amazon EC2 Volume object.

    Raises:
      RuntimeError: If volume does not exist.
    """
    volumes = self.ListVolumes(region=region)
    volume = volumes.get(volume_id)
    if not volume:
      error_msg = 'Volume {0:s} was not found in AWS account'.format(
          volume_id)
      raise RuntimeError(error_msg)

    if not region:
      region = self.default_region

    zone = volume['zone']

    return AwsVolume(volume_id, self, region, zone)

  def __GetVolumeByName(self, volume_name, region=None):
    """Get a volume from an AWS account by its name tag.

    Args:
      volume_name (str): The volume name tag.
      region (str): The region to look the volume in.

    Returns:
      AwsVolume: An Amazon EC2 Volume object.

    Raises:
      RuntimeError: If volume does not exist, or if multiple volumes have the
      same name tag.
    """
    volume_id = None
    count = 0
    volumes = self.ListVolumes(region=region)
    for key in volumes:
      if volumes[key].get('name', None) == volume_name:
        volume_id = key
        count += 1

    if count == 0:
      error_msg = 'Volume {0:s} was not found in AWS account'.format(
          volume_name)
      raise RuntimeError(error_msg)
    if count > 1:
      error_msg = 'Multiple volumes with tag name {0:s} were found in the ' \
                  'AWS account. Please look-up the volume by its unique AWS ' \
                  'volume-ID instead'.format(volume_name)
      raise RuntimeError(error_msg)

    if not region:
      region = self.default_region

    zone = volumes[volume_id]['zone']

    return AwsVolume(volume_id, self, region, zone, name=volume_name)


class AwsInstance:
  """Class representing an AWS EC2 instance.

  Attributes:
    aws_account (AwsAccount): The account for the instance.
    instance_id (str): The id of the instance.
    region (str): The region the instance is in.
    availability_zone (str): The zone within the region in which the instance
    is.
    name (str): the name tag (if any) of the instance.
  """
  def __init__(self, aws_account, instance_id, region,
               availability_zone, name=None):
    """Initialize the AWS EC2 instance.

    Attributes:
      aws_account (AwsAccount): The account for the instance.
      instance_id (str): The id of the instance.
      region (str): The region the instance is in.
      availability_zone (str): The zone within the region in which the instance
      is.
      name (str): the name tag (if any) of the instance.
    """
    self.aws_account = aws_account
    self.instance_id = instance_id
    self.region = region
    self.availability_zone = availability_zone
    self.name = name

  def GetBootVolume(self):
    """Get the instance's boot volume.

    Returns:
      AwsVolume: Volume object if the volume is found.

    Raises:
      RuntimeError: If no boot volume could be found.
    """
    boot_device = self.aws_account.ResourceApi(
        EC2_SERVICE).Instance(self.instance_id).root_device_name
    volumes = self.ListVolumes()

    for volume_id in volumes:
      if volumes[volume_id]['device'] == boot_device:
        return AwsVolume(volume_id, self.aws_account, self.region,
                         self.availability_zone)

    error_msg = 'Boot volume not found for instance: {0:s}'.format(
        self.instance_id)
    raise RuntimeError(error_msg)

  def ListVolumes(self):
    """List all volumes for the instance.

    Returns:
      dict: Dict of volume ids.
    """
    return self.aws_account.ListVolumes(
        filters=[dict(Name='attachment.instance-id', Values=[
            self.instance_id])]
    )


class AwsElasticBlockStore:
  """Class representing an AWS EBS resource.

  Attributes:
    aws_account (AwsAccount): The account for the resource.
    region (str): The region the EBS is in.
    availability_zone (str): The zone within the region in which the EBS is.
    name (str): The name tag (if any) of the EBS resource.
  """
  def __init__(self, aws_account, region, availability_zone, name):
    """Initialize the AWS EBS resource.

    Attributes:
      aws_account (AwsAccount): The account for the resource.
      region (str): The region the EBS is in.
      availability_zone (str): The zone within the region in which the EBS is.
      name (str): The name tag (if any) of the EBS resource.
    """
    self.aws_account = aws_account
    self.region = region
    self.availability_zone = availability_zone
    self.name = name


class AwsVolume(AwsElasticBlockStore):
  """Class representing an AWS EBS volume.

  Attributes:
    volume_id (str): The id of the volume.
    aws_account (AwsAccount): The account for the volume.
    region (str): The region the volume is in.
    availability_zone (str): The zone within the region in which the volume is.
    name (str): The name tag (if any) of the volume.
  """
  def __init__(self, volume_id, aws_account, region, availability_zone,
               name=None):
    """Initialize an AWS EBS volume.

    Attributes:
      volume_id (str): The id of the volume.
      aws_account (AwsAccount): The account for the volume.
      region (str): The region the volume is in.
      availability_zone (str): The zone within the region in which the volume
      is.
      name (str): The name tag (if any) of the volume.
    """
    super(AwsVolume, self).__init__(aws_account, region, availability_zone,
                                    name)
    self.volume_id = volume_id

  def Snapshot(self, snapshot_name=None):
    """Create a snapshot of the volume.

    Args:
      snapshot_name (str): Name tag of the snapshot.

    Returns:
      AwsSnapshot: A snapshot object.

    Raises:
      ValueError: if the snapshot name does not comply with the RegEx.
      RuntimeError: If the snapshot could not be created.
    """

    timestamp = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
    if not snapshot_name:
      snapshot_name = self.volume_id
    truncate_at = 255 - len(timestamp) - 1
    snapshot_name = '{0}-{1}'.format(snapshot_name[:truncate_at], timestamp)
    if not REGEX_TAG_VALUE.match(snapshot_name):
      raise ValueError('Error: snapshot name {0:s} does not comply with '
                       '{1:s}'.format(snapshot_name, REGEX_TAG_VALUE.pattern))

    client = self.aws_account.ClientApi(EC2_SERVICE)
    try:
      snapshot = client.create_snapshot(
          VolumeId=self.volume_id,
          TagSpecifications=[GetTagForResourceType('snapshot', snapshot_name)]
      )
      snapshot_id = snapshot.get('SnapshotId')
      # Wait for snapshot completion
      client.get_waiter('snapshot_completed').wait(SnapshotIds=[snapshot_id])
    except client.exceptions.ClientError as exception:
      raise RuntimeError('Error: could not create snapshot for volume {0:s}: '
                         '{1:s}'.format(self.volume_id, str(exception)))

    return AwsSnapshot(snapshot_id, self, name=snapshot_name)


class AwsSnapshot(AwsElasticBlockStore):
  """Class representing an AWS EBS snapshot.

  Attributes:
    snapshot_id (str): The id of the snapshot.
    volume (AwsVolume): The volume from which the snapshot was taken.
    name (str): The name tag (if any) of the snapshot.
  """
  def __init__(self, snapshot_id, volume, name=None):
    """Initialize an AWS EBS snapshot.

    Attributes:
      snapshot_id (str): The id of the snapshot.
      volume (AwsVolume): The volume from which the snapshot was taken.
      name (str): The name tag (if any) of the snapshot.
    """
    super(AwsSnapshot, self).__init__(volume.aws_account, volume.region,
                                      volume.availability_zone, name)
    self.snapshot_id = snapshot_id
    self.volume = volume

  def Delete(self):
    """Delete a snapshot."""
    client = self.aws_account.ClientApi(EC2_SERVICE)
    try:
      client.delete_snapshot(
          SnapshotId=self.snapshot_id
      )
    except client.exceptions.ClientError as exception:
      raise RuntimeError('Error: could not delete snapshot {0:s}: {1:s}'.format(
          self.snapshot_id, str(exception)))


def CreateVolumeCopy(instance_name, zone, volume_name=None):
  """Create a copy of an AWS EBS Volume.

  Attributes:
    instance_name (str): Instance using the volume to be copied.
    zone (str): The zone within the region to create the new resource in.
    volume_name (str): Name of the volume to copy. If None, boot volume will be
    copied.

  Returns:
    AwsVolume: An AWS EBS Volume object.

  Raises:
    RuntimeError: If there are errors copying the volume.
  """
  aws_account = AwsAccount(zone)
  instance = aws_account.GetInstance(instance_name) if instance_name else None

  try:
    if volume_name:
      volume_to_copy = aws_account.GetVolume(volume_name)
    else:
      volume_to_copy = instance.GetBootVolume()

    log.info('Volume copy of {0:s} started...'.format(volume_to_copy.volume_id))
    snapshot = volume_to_copy.Snapshot()
    new_volume = aws_account.CreateVolumeFromSnapshot(
        snapshot, volume_name_prefix='evidence'
    )
    snapshot.Delete()
    log.info(
        'Volume {0:s} successfully copied to {1:s}'.format(
            volume_to_copy.volume_id, new_volume.volume_id))

  except RuntimeError as exception:
    error_msg = 'Error copying volume "{0:s}": {1!s}'.format(
        volume_name, exception)
    raise RuntimeError(error_msg)

  return new_volume


def GetTagForResourceType(resource, name):
  """Create a dictionary for AWS Tag Specifications.

  Attributes:
    resource (str): The type of AWS resource.
    name (str): The name of the resource.

  Returns:
    dict: A dictionary for AWS Tag Specifications.
  """
  return dict(
      ResourceType=resource,
      Tags=[
          dict(
              Key='Name',
              Value=name
          )
      ]
  )
