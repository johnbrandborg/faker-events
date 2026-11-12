"""Sphinx configuration for the Faker Events documentation."""

import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.abspath(".."))

import faker_events

# -- Project information -----------------------------------------------------

project = "Faker Events"
copyright = f"2020-{datetime.now().year}, John Brandborg"
author = "John Brandborg"
version = faker_events.__version__
release = faker_events.__version__

# -- General configuration ---------------------------------------------------

extensions = [
    "myst_parser",
    "sphinx.ext.autodoc",
    "sphinx.ext.intersphinx",
    "sphinx.ext.todo",
    "sphinx.ext.viewcode",
    "sphinx_copybutton",
    "sphinx_design",
    "sphinxext.opengraph",
]

templates_path = ["_templates"]
exclude_patterns = ["README.md", "_build", "Thumbs.db", ".DS_Store"]
todo_include_todos = True

myst_enable_extensions = [
    "colon_fence",
]

# -- Options for HTML output -------------------------------------------------

html_theme = "furo"
html_static_path = ["_static"]
html_theme_options = {
    "source_repository": "https://github.com/johnbrandborg/faker-events",
    "source_branch": "main",
    "source_directory": "docs/",
}

# -- Intersphinx mapping -----------------------------------------------------

intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "faker": ("https://faker.readthedocs.io/en/stable/", None),
    "pydantic": ("https://docs.pydantic.dev/latest/", None),
}

# -- Copy button settings ----------------------------------------------------

copybutton_prompt_text = r"^\$ "
copybutton_prompt_is_regexp = True

# -- Open Graph settings -----------------------------------------------------

ogp_site_url = "https://faker-events.readthedocs.io/en/latest/"
ogp_description_length = 200
