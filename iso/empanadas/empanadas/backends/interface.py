"""
empanadas backend interface
"""
from abc import ABC, abstractmethod


class BackendInterface(ABC):
    """
    Interface to build images (or whatever)
    """
    @abstractmethod
    def prepare(self):
        """
        Prepares the environment necessary for building the image.
        This might include setting up directories, checking prerequisites, etc.
        """

    @abstractmethod
    def build(self):
        """
        Performs the image build operation. This is the core method
        where the actual image building logic is implemented.
        """

    @abstractmethod
    def stage(self):
        """
        Transforms and copies artifacts from build directory to the 
        location expected by the builder (usually in /tmp/)
        """

    @abstractmethod
    def clean(self):
        """
        Cleans up any resources or temporary files created during
        the image building process.
        """
