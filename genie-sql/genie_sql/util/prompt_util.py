# -*- coding: utf-8 -*-
# =====================
#
#
# Author: liumin.423
# Date:   2025/7/7
# =====================
import importlib.resources

import yaml


def get_prompt(prompt_file):
    prompt_pkg = importlib.resources.files("genie_sql.prompt")
    return yaml.safe_load(prompt_pkg.joinpath(f"{prompt_file}.yaml").read_text())
