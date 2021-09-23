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
from unittest import mock

from libcloudforensics import errors
from libcloudforensics.providers.kubernetes import base
from libcloudforensics.providers.kubernetes import workloads
from tests.providers.kubernetes import k8s_mocks


@mock.patch.object(workloads.K8sWorkload, '__abstractmethods__', set())
@mock.patch.object(workloads.K8sWorkload, '_PodMatchLabels')
class K8sWorkloadTest(unittest.TestCase):
  """Test K8sWorkload API calls."""

  # pylint: disable=abstract-class-instantiated

  mock_match_labels = {'app': 'nginx-klzkdoho'}

  @typing.no_type_check
  def testIsCoveringPodSameLabels(self, workload_pod_match_labels):
    """Test that a pod is indeed covered by a workload."""
    # Patch abstract method
    workload_pod_match_labels.return_value = self.mock_match_labels
    workload = workloads.K8sWorkload(
        k8s_mocks.MOCK_API_CLIENT, 'name', 'namespace')

    mock_pod_response = k8s_mocks.V1Pod(labels=self.mock_match_labels)
    mock_pod = base.K8sPod(k8s_mocks.MOCK_API_CLIENT, 'name', 'namespace')

    with mock.patch.object(mock_pod, 'Read') as mock_pod_read:
      mock_pod_read.return_value = mock_pod_response
      self.assertTrue(workload.IsCoveringPod(mock_pod))

  @typing.no_type_check
  def testIsCoveringPodDifferentLabels(self, workload_pod_match_labels):
    """Test that a pod is not covered by a workload with different labels."""
    # Patch abstract method
    workload_pod_match_labels.return_value = self.mock_match_labels
    workload = workloads.K8sWorkload(
        k8s_mocks.MOCK_API_CLIENT, 'name', 'namespace')

    mock_pod_response = k8s_mocks.V1Pod(labels={})
    mock_pod = base.K8sPod(k8s_mocks.MOCK_API_CLIENT, 'name', 'namespace')

    with mock.patch.object(mock_pod, 'Read') as mock_pod_read:
      mock_pod_read.return_value = mock_pod_response
      self.assertFalse(workload.IsCoveringPod(mock_pod))

  @typing.no_type_check
  def testIsCoveringPodDifferentNamespace(self, workload_pod_match_labels):
    """Test that pod is not covered by workload with different namespace."""
    # Patch abstract method
    workload_pod_match_labels.return_value = self.mock_match_labels
    workload = workloads.K8sWorkload(
        k8s_mocks.MOCK_API_CLIENT, 'name', 'namespace')

    mock_pod_response = k8s_mocks.V1Pod(labels=self.mock_match_labels)
    mock_pod = base.K8sPod(k8s_mocks.MOCK_API_CLIENT, 'name', 'production')

    with mock.patch.object(mock_pod, 'Read') as mock_pod_read:
      mock_pod_read.return_value = mock_pod_response
      self.assertFalse(workload.IsCoveringPod(mock_pod))

  @typing.no_type_check
  @mock.patch('kubernetes.client.CoreV1Api.list_namespaced_pod')
  def testListPodWithCorrectArgs(
      self, mock_list_pod, workload_pod_match_labels):
    """Test that workload pods are listed with correct arguments."""
    # Override abstract method
    workload_pod_match_labels.return_value = self.mock_match_labels
    workload = workloads.K8sWorkload(
        k8s_mocks.MOCK_API_CLIENT, 'name', 'namespace-xdwvkhrj')
    workload.GetCoveredPods()

    mock_list_pod.assert_called_with(
        'namespace-xdwvkhrj', label_selector='app=nginx-klzkdoho')


class K8sDeploymentTest(unittest.TestCase):
  """Test K8sDeployment API calls and necessary supporting functions."""

  @typing.no_type_check
  @mock.patch('kubernetes.client.AppsV1Api.delete_namespaced_replica_set')
  def testReplicaSetNonCascadingDeletionArgs(self, mock_delete):
    """Test that a ReplicaSet's deletion specifies correct args."""
    workload = workloads.K8sReplicaSet(
        k8s_mocks.MOCK_API_CLIENT, 'name-cvjcofvh', 'namespace-gonnujrl')
    workload.Delete(cascade=False)

    mock_delete.assert_called_once_with(
        'name-cvjcofvh',
        'namespace-gonnujrl',
        body={'propagationPolicy': 'Orphan'})

  @typing.no_type_check
  @mock.patch('kubernetes.client.AppsV1Api.delete_namespaced_deployment')
  def testDeploymentNonCascadingDeletionArgs(self, mock_delete):
    """Test that a Deployment's deletion specifies correct args."""
    workload = workloads.K8sDeployment(
        k8s_mocks.MOCK_API_CLIENT, 'name-cvjcofvh', 'namespace-gonnujrl')
    workload.Delete(cascade=False)

    mock_delete.assert_called_once_with(
        'name-cvjcofvh',
        'namespace-gonnujrl',
        body={'propagationPolicy': 'Orphan'})

  @typing.no_type_check
  @mock.patch('kubernetes.client.AppsV1Api.list_namespaced_replica_set')
  def testDeploymentReplicaSet(self, mock_list_replica_set):
    """Test that a ReplicaSet matching the Deployment's spec is returned."""
    mock_list_replica_set.return_value.items = [
        k8s_mocks.V1ReplicaSet(name='replicaset-0', template_spec_labels={}),
        k8s_mocks.V1ReplicaSet(name='replicaset-1', template_spec_labels={}),
        k8s_mocks.V1ReplicaSet(name='replicaset-2', template_spec_labels={}),
        k8s_mocks.V1ReplicaSet(name='replicaset-3', template_spec_labels={}),
        k8s_mocks.V1ReplicaSet(
            name='replicaset-4',
            template_spec_labels={
                'app': 'nginx', 'pod-template-hash': 'abcd'
            }),
        k8s_mocks.V1ReplicaSet(name='replicaset-5', template_spec_labels={}),
        k8s_mocks.V1ReplicaSet(name='replicaset-6', template_spec_labels={}),
        k8s_mocks.V1ReplicaSet(name='replicaset-7', template_spec_labels={}),
        k8s_mocks.V1ReplicaSet(name='replicaset-8', template_spec_labels={}),
        k8s_mocks.V1ReplicaSet(name='replicaset-9', template_spec_labels={}),
    ]

    deployment = workloads.K8sDeployment(
        k8s_mocks.MOCK_API_CLIENT, 'deployment', 'default')
    with mock.patch.object(deployment, 'Read') as mock_read:
      mock_read.return_value = k8s_mocks.V1Deployment(
          template_spec_labels={'app': 'nginx'},
          # Match labels are not important here since API return value is
          # predefined
          match_labels={})
      self.assertEqual('replicaset-4', deployment._ReplicaSet().name)  # pylint: disable=protected-access

  @typing.no_type_check
  @mock.patch('kubernetes.client.AppsV1Api.list_namespaced_replica_set')
  def testDeploymentReplicaSetError(self, mock_list_replica_set):
    """Test error is raised if no ReplicaSet matches Deployment."""
    mock_list_replica_set.return_value.items = [
        k8s_mocks.V1ReplicaSet(name='replicaset-0', template_spec_labels={}),
    ]

    deployment = workloads.K8sDeployment(
        k8s_mocks.MOCK_API_CLIENT, 'deployment', 'default')
    with mock.patch.object(deployment, 'Read') as mock_deployment_read:
      mock_deployment_read.return_value = k8s_mocks.V1Deployment(
          template_spec_labels={'app': 'nginx'},
          # Match labels are not important here since API return value is
          # predefined
          match_labels={})
      self.assertRaises(errors.ResourceNotFoundError, deployment._ReplicaSet)  # pylint: disable=protected-access
