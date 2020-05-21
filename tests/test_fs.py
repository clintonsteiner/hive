from unittest import TestCase
from pathlib import Path
import tempfile
import yaml
import os
from hive.util.fs import global_hive_config_search
from hive.config import GlobalConfig


class TestDictReaderStepper(TestCase):

    def test_global_hive_config_search_finds_default(self):
        result = global_hive_config_search()
        self.assertIsInstance(result, GlobalConfig, "should be a GlobalConfig class instance")
        self.assertTrue(result.log_run, "should have picked up the default config where this value is set")

    def test_global_hive_config_search_finds_parent(self):
        with tempfile.TemporaryDirectory() as parent:
            root_path = Path(parent)
            parent_hive_file = root_path.joinpath(".hive.yaml")
            with open(parent_hive_file, 'w') as file:
                yaml.safe_dump({"log_sim": False}, file)
            with tempfile.TemporaryDirectory(dir=parent) as child:
                os.chdir(child)
                result = global_hive_config_search()
                self.assertIsInstance(result, GlobalConfig, "should be a GlobalConfig class instance")
                self.assertFalse(result.log_sim, "should have found the modified config in the parent directory")  # default is "True"
                self.assertTrue(result.log_run, "should also contain keys from the default config")
