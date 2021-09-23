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
"""Test on netpol Kubernetes objects."""

import typing
import unittest

import mock
from kubernetes import client

from libcloudforensics.providers.kubernetes import netpol
from tests.providers.kubernetes import k8s_mocks


@mock.patch.object(netpol.K8sNetworkPolicyWithSpec, '__abstractmethods__', ())
@mock.patch.object(client.NetworkingV1Api, 'create_namespaced_network_policy')
class K8sNetworkPolicyWithSpecCreationTest(unittest.TestCase):
  """Test the K8sNetworkPolicyWithSpec's creation API call."""

  # pylint: disable=abstract-class-instantiated

  mock_spec = mock.Mock()

  @typing.no_type_check
  @mock.patch.object(netpol.K8sNetworkPolicyWithSpec, '_spec', mock_spec)
  def testNetworkPolicyCreationNamespace(self, mock_create_func):
    """Test that creating a network policy provides the correct namespace."""
    network_policy = netpol.K8sNetworkPolicyWithSpec(
        k8s_mocks.MOCK_API_CLIENT, 'name', 'namespace-iwlgvtpb')
    network_policy.Create()
    self.assertEqual('namespace-iwlgvtpb', mock_create_func.call_args.args[0])

  @typing.no_type_check
  @mock.patch.object(netpol.K8sNetworkPolicyWithSpec, '_spec', mock_spec)
  def testNetworkPolicyCreationSpec(self, mock_create_func):
    """Test that creating a network policy provides the correct spec."""
    network_policy = netpol.K8sNetworkPolicyWithSpec(
        k8s_mocks.MOCK_API_CLIENT, 'name', 'namespace')
    network_policy.Create()
    self.assertEqual(self.mock_spec, mock_create_func.call_args.args[1].spec)

  @typing.no_type_check
  @mock.patch.object(netpol.K8sNetworkPolicyWithSpec, '_spec', mock_spec)
  def testNetworkPolicyCreationMetadata(self, mock_create_func):
    """Test that creating a network policy provides the correct metadata."""
    network_policy = netpol.K8sNetworkPolicyWithSpec(
        k8s_mocks.MOCK_API_CLIENT, 'name-jsdukbvx', 'namespace-jsdukbvx')
    network_policy.Create()
    self.assertEqual(
        client.V1ObjectMeta(
            name='name-jsdukbvx', namespace='namespace-jsdukbvx'),
        mock_create_func.call_args.args[1].metadata)


@mock.patch.object(client.NetworkingV1Api, 'create_namespaced_network_policy')
class K8sDenyAllNetworkPolicyCreationTest(unittest.TestCase):
  """Test K8sDenyAllNetworkPolicy creation API call."""

  @typing.no_type_check
  def testIsDenyAllNetworkPolicyCreationSpec(self, mock_create_func):
    """Test that a deny-all network policy creation has deny-all spec."""
    network_policy = netpol.K8sDenyAllNetworkPolicy(
        k8s_mocks.MOCK_API_CLIENT, 'default')
    network_policy.Create()
    # Check that given network policy is a deny-all policy
    provided_spec = mock_create_func.call_args.args[1].spec
    self.assertEqual(['Ingress', 'Egress'], provided_spec.policy_types)
    self.assertIsNone(provided_spec.ingress)
    self.assertIsNone(provided_spec.egress)


class K8sNetworkPolicyTest(unittest.TestCase):
  """Test that K8sNetworkPolicy calls Kubernetes API correctly."""

  @typing.no_type_check
  @mock.patch.object(client.NetworkingV1Api, 'read_namespaced_network_policy')
  def testNetworkPolicyReadArgs(self, mock_read_func):
    """Test that a NetworkPolicy read is called with the correct args."""
    network_policy = netpol.K8sNetworkPolicy(
        k8s_mocks.MOCK_API_CLIENT, 'name-arvvbdxl', 'namespace-arvvbdxl')
    network_policy.Read()
    mock_read_func.assert_called_once_with(
        'name-arvvbdxl', 'namespace-arvvbdxl')

  @typing.no_type_check
  @mock.patch.object(client.NetworkingV1Api, 'delete_namespaced_network_policy')
  def testNetworkPolicyDeleteArgs(self, mock_delete_func):
    """Test that a NetworkPolicy deletion is called with the correct args."""
    network_policy = netpol.K8sNetworkPolicy(
        k8s_mocks.MOCK_API_CLIENT, 'name-iyykyqbc', 'namespace-iyykyqbc')
    network_policy.Delete()
    mock_delete_func.assert_called_once_with(
        'name-iyykyqbc', 'namespace-iyykyqbc')
