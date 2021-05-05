# -*- coding: utf-8 -*-
# Copyright 2021 Google Inc.
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
"""Bucket functionality."""

import os
from typing import TYPE_CHECKING, Dict, Optional, Any

from libcloudforensics import errors
from libcloudforensics import logging_utils
from libcloudforensics.providers.aws.internal import common

logging_utils.SetUpLogger(__name__)
logger = logging_utils.GetLogger(__name__)

if TYPE_CHECKING:
  # TYPE_CHECKING is always False at runtime, therefore it is safe to ignore
  # the following cyclic import, as it it only used for type hints
  from libcloudforensics.providers.aws.internal import account  # pylint: disable=cyclic-import


class S3:
  """Class that represents AWS S3 storage services.

  Attributes:
    aws_account (AWSAccount): The account for the resource.
    name (str): The name of the bucket.
    region (str): The region in which the bucket resides.
  """

  def __init__(self,
               aws_account: 'account.AWSAccount') -> None:
    """Initialize the AWS S3 resource.

    Args:
      aws_account (AWSAccount): The account for the resource.
    """

    self.aws_account = aws_account

  def CreateBucket(
      self,
      name: str,
      region: Optional[str] = None,
      acl: str = 'private') -> Dict[str, Any]:
    """Create an S3 storage bucket.

    Args:
      name (str): The name of the bucket.
      region (str): Optional. The region in which the bucket resides.
      acl (str): Optional. The canned ACL with which to create the bucket.
        Default is 'private'.
    Appropriate values for the Canned ACLs are here:
    https://docs.aws.amazon.com/AmazonS3/latest/userguide/acl-overview.html#canned-acl  # pylint: disable=line-too-long

    Returns:
      Dict: An API operation object for a S3 bucket.
        https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/s3.html#S3.Bucket.create  # pylint: disable=line-too-long

    Raises:
      ResourceCreationError: If the bucket couldn't be created.
    """

    client = self.aws_account.ClientApi(common.S3_SERVICE)
    try:
      bucket = client.create_bucket(
          Bucket=name,
          ACL=acl,
          CreateBucketConfiguration={
              'LocationConstraint': region or self.aws_account.default_region
          })
      return bucket
    except client.exceptions.BucketAlreadyOwnedByYou as exception:
      raise errors.ResourceCreationError(
          'Bucket {0:s} already exists: {1:s}'.format(
              name, str(exception)),
          __name__) from exception
    except client.exceptions.ClientError as exception:
      raise errors.ResourceCreationError(
          'Could not create bucket {0:s}: {1:s}'.format(
              name, str(exception)),
          __name__) from exception

  def Put(self, s3_path, local_file) -> None:
    """Upload a local file to an S3 bucket.

    Args:
      s3_path (str): Path to the target S3 bucket.
          Ex: s3://test/bucket
      local_file (str): Path to the file to be uploaded.
          Ex: /tmp/myfile
    Raises:
      ResourceCreationError: If the object couldn't be uploaded.
    """
    client = self.aws_account.ClientApi(common.S3_SERVICE)
    if s3_path.startswith('s3://'):
      s3_path = s3_path[5:]
    try:
      client.upload_file(local_file, s3_path, os.path.basename(local_file))
    except FileNotFoundError as exception:
      raise errors.ResourceNotFoundError(
          'Could not upload file {0:s}: {1:s}'.format(
              local_file, str(exception)),
          __name__) from exception
    except client.exceptions.ClientError as exception:
      raise errors.ResourceCreationError(
          'Could not upload file {0:s}: {1:s}'.format(
              local_file, str(exception)),
          __name__) from exception
