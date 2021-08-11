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
"""Kubernetes functionalities."""

import abc
from collections import defaultdict
from typing import Dict

import kubernetes.client


class K8sResource(abc.ABC):
  """Abstract class encompassing Kubernetes resources."""

  @abc.abstractmethod
  def _K8sApi(self) -> kubernetes.client.ApiClient:
    """Creates an authenticated Kubernetes API client.

    Returns:
      kubernetes.client.ApiClient: An authenticated client to
        the Kubernetes API server.
    """


class K8sSelector:
  """Class to build K8s API selectors."""

  class Component(abc.ABC):
    """Component of the selector."""

    @abc.abstractmethod
    def ToString(self):
      """Returns the component of the selector."""

    @property
    @abc.abstractmethod
    def Keyword(self):
      """Returns the keyword to which the selector component belongs"""

  class LabelComponent(Component):

    @property
    def Keyword(self):
      return 'label_selector'

  class FieldComponent(Component):

    @property
    def Keyword(self):
      return 'field_selector'

  class Name(FieldComponent):
    """Selector component for having a particular name"""

    def __init__(self, name: str):
      super().__init__()
      self.name = name

    def ToString(self):
      return 'metadata.name={0:s}'.format(self.name)

  class Node(FieldComponent):
    """Selector component for running on a particular node."""

    def __init__(self, node) -> None:
      super().__init__()
      self.node = node

    def ToString(self):
      return 'spec.nodeName={0:s}'.format(self.node)

  class Running(FieldComponent):
    """Selector component for a running pod."""

    def ToString(self):
      return 'status.phase!=Failed,status.phase!=Succeeded'

  class Label(LabelComponent):

    def __init__(self, key: str, value: str):
      self.key = key
      self.value = value

    def ToString(self):
      return '{0:s}={1:s}'.format(self.key, self.value)

  def __init__(self, *selectors: Component):
    self.selectors = selectors

  def ToKeywords(self):
    """Builds the selector string to be passed to the K8s API."""
    keywords = defaultdict(list)
    for selector in self.selectors:
      keywords[selector.Keyword].append(selector.ToString())
    return {k: ','.join(vs) for k, vs in keywords.items()}

  @classmethod
  def FromDict(cls, labels: Dict[str, str]):
    args = map(lambda k: K8sSelector.Label(k, labels[k]), labels)
    return cls(*args)