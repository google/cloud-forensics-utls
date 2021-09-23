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
from libcloudforensics.providers.kubernetes import cluster
from tests.providers.kubernetes import k8s_mocks


class K8sClusterTest(unittest.TestCase):
  """Test K8sCluster functionality, mainly checking API calls."""

  @typing.no_type_check
  @mock.patch('kubernetes.client.CoreV1Api')
  def testClusterListNodes(self, mock_k8s_api):
    """Test that nodes of a cluster are correctly listed."""

    # Create and assign mocks
    mock_nodes = k8s_mocks.V1NodeList(5)
    mock_k8s_api_func = mock_k8s_api.return_value.list_node
    mock_k8s_api_func.return_value = mock_nodes

    nodes = cluster.K8sCluster(api_client=k8s_mocks.MOCK_API_CLIENT).ListNodes()

    # Assert API and corresponding function was called appropriately
    mock_k8s_api.assert_called_with(k8s_mocks.MOCK_API_CLIENT)
    mock_k8s_api_func.assert_called()
    # Assert returned nodes correspond to provided response
    self.assertEqual(
        set(node.name for node in nodes),
        set(node.metadata.name for node in mock_nodes.items))

  @typing.no_type_check
  @mock.patch('kubernetes.client.CoreV1Api')
  def testClusterListPods(self, mock_k8s_api):
    """Test that pods of a cluster are correctly listed."""

    # Create and assign mocks
    mock_pods = k8s_mocks.V1PodList(5)
    mock_k8s_api_func = mock_k8s_api.return_value.list_pod_for_all_namespaces
    mock_k8s_api_func.return_value = mock_pods

    pods = cluster.K8sCluster(api_client=k8s_mocks.MOCK_API_CLIENT).ListPods()

    # Assert API and corresponding function was called appropriately
    mock_k8s_api.assert_called_with(k8s_mocks.MOCK_API_CLIENT)
    mock_k8s_api_func.assert_called()
    # Assert returned pods correspond to provided response
    self.assertEqual(
        set(pod.name for pod in pods),
        set(pod.metadata.name for pod in mock_pods.items))

  @typing.no_type_check
  @mock.patch('kubernetes.client.CoreV1Api')
  def testClusterListNamespacedPods(self, mock_k8s_api):
    """Test that namespaced pods of a cluster are correctly listed."""

    # Create and assign mocks
    mock_namespace = mock.Mock()
    mock_pods = k8s_mocks.V1PodList(5)
    mock_k8s_api_func = mock_k8s_api.return_value.list_namespaced_pod
    mock_k8s_api_func.return_value = mock_pods

    pods = cluster.K8sCluster(
        api_client=k8s_mocks.MOCK_API_CLIENT).ListPods(mock_namespace)

    # Assert API and corresponding function was called appropriately
    mock_k8s_api.assert_called_with(k8s_mocks.MOCK_API_CLIENT)
    mock_k8s_api_func.assert_called_with(mock_namespace)
    # Assert returned pods correspond to provided response
    self.assertEqual(
        set(pod.name for pod in pods),
        set(pod.metadata.name for pod in mock_pods.items))


class K8sNodeTest(unittest.TestCase):
  """Test K8sCluster functionality, mainly checking API calls."""

  @typing.no_type_check
  @mock.patch('kubernetes.client.CoreV1Api')
  def testNodeListPods(self, mock_k8s_api):
    """Test that pods on a node are correctly listed."""

    # Create and assign mocks
    mock_pods = k8s_mocks.V1PodList(5)
    mock_k8s_api_func = mock_k8s_api.return_value.list_pod_for_all_namespaces
    mock_k8s_api_func.return_value = mock_pods

    pods = base.K8sNode(k8s_mocks.MOCK_API_CLIENT, 'fake-node-name').ListPods()

    # Assert API and corresponding function was called appropriately
    mock_k8s_api.assert_called_with(k8s_mocks.MOCK_API_CLIENT)
    mock_k8s_api_func.assert_called()
    kwargs = mock_k8s_api_func.call_args.kwargs
    self.assertIn('field_selector', kwargs)
    self.assertIn('fake-node-name', kwargs['field_selector'])
    # Assert returned pods correspond to provided response
    self.assertEqual(
        set(pod.name for pod in pods),
        set(pod.metadata.name for pod in mock_pods.items))


class K8sPodTest(unittest.TestCase):
  """Test K8sPod functionality, mainly checking API calls."""

  @typing.no_type_check
  @mock.patch('kubernetes.client.CoreV1Api')
  def testPodGetNode(self, mock_k8s_api):
    """Test that the returned node of a pod is correct."""
    mock_pod = k8s_mocks.V1Pod(
        name='fake-pod-name',
        namespace='fake-namespace',
        node_name='fake-node-name')
    mock_k8s_api_func = mock_k8s_api.return_value.read_namespaced_pod
    mock_k8s_api_func.return_value = mock_pod

    node = base.K8sPod(
        k8s_mocks.MOCK_API_CLIENT, 'fake-pod-name', 'fake-namespace').GetNode()

    # Assert API and corresponding function was called appropriately
    mock_k8s_api.assert_called_with(k8s_mocks.MOCK_API_CLIENT)
    mock_k8s_api_func.assert_called()
    self.assertEqual(('fake-pod-name', 'fake-namespace'),
                     mock_k8s_api_func.call_args.args)
    # Assert returned pods correspond to provided response
    self.assertEqual('fake-node-name', node.name)
