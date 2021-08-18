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
"""Test on base Kubernetes objects."""

import typing
import unittest

import mock

from libcloudforensics.providers.kubernetes import base
from tests.providers.kubernetes import k8s_mocks


class K8sBaseTest(unittest.TestCase):
  """Test functionality on base Kubernetes object, mainly checking API calls."""

  @typing.no_type_check
  @mock.patch('kubernetes.client.CoreV1Api')
  def testClusterListNodes(self, mock_k8s_api):
    """Test that nodes of a cluster are correctly listed."""

    # Create and assign mocks
    mock_nodes = k8s_mocks.MakeMockNodes(5)
    mock_k8s_api_func = mock_k8s_api.return_value.list_node
    mock_k8s_api_func.return_value = mock_nodes

    nodes = base.K8sCluster(api_client=k8s_mocks.MOCK_API_CLIENT).ListNodes()

    # Assert API and corresponding function was called appropriately
    self.assertTrue(mock_k8s_api.called_with(k8s_mocks.MOCK_API_CLIENT))
    self.assertTrue(mock_k8s_api_func.called)
    # Assert returned nodes correspond to provided response
    self.assertEqual(set(node.name for node in nodes),
                     set(node.metadata.name for node in mock_nodes.items))

  @typing.no_type_check
  @mock.patch('kubernetes.client.CoreV1Api')
  def testClusterListPods(self, mock_k8s_api):
    """Test that pods of a cluster are correctly listed."""

    # Create and assign mocks
    mock_pods = k8s_mocks.MakeMockNodes(5)
    mock_k8s_api_func = mock_k8s_api.return_value.list_pod_for_all_namespaces
    mock_k8s_api_func.return_value = mock_pods

    pods = base.K8sCluster(api_client=k8s_mocks.MOCK_API_CLIENT).ListPods()

    # Assert API and corresponding function was called appropriately
    self.assertTrue(mock_k8s_api.called_with(k8s_mocks.MOCK_API_CLIENT))
    self.assertTrue(mock_k8s_api_func.called)
    # Assert returned pods correspond to provided response
    self.assertEqual(set(pod.name for pod in pods),
                     set(pod.metadata.name for pod in mock_pods.items))

  @typing.no_type_check
  @mock.patch('kubernetes.client.CoreV1Api')
  def testClusterListNamespacedPods(self, mock_k8s_api):
    """Test that namespaced pods of a cluster are correctly listed."""

    # Create and assign mocks
    mock_namespace = mock.Mock()
    mock_pods = k8s_mocks.MakeMockNodes(5)
    mock_k8s_api_func = mock_k8s_api.return_value.list_namespaced_pod
    mock_k8s_api_func.return_value = mock_pods

    pods = base.K8sCluster(api_client=k8s_mocks.MOCK_API_CLIENT).ListPods(
      mock_namespace
    )

    # Assert API and corresponding function was called appropriately
    self.assertTrue(mock_k8s_api.called_with(k8s_mocks.MOCK_API_CLIENT))
    self.assertTrue(mock_k8s_api_func.called_with(mock_namespace))
    # Assert returned pods correspond to provided response
    self.assertTrue(set(pod.name for pod in pods),
                    set(pod.metadata.name for pod in mock_pods.items))
